"""Braço A3: PLS sobre as bandas selecionadas por iPLS (ADR 012).

A seleção de intervalos vem do `mdatools::ipls` via `rpy2` — implementação
estabelecida, como o pipeline manda —, mas a REGRESSÃO é o mesmo
`PLSRegression` do `PLSArm`. Assim A1 e A3 diferem por exatamente uma
característica, o subconjunto de variáveis, que é o que torna
$\\Delta$ interpretável. Se o mdatools também ajustasse o modelo final,
qualquer diferença de implementação do PLS entraria no termo junto com o
efeito da seleção.

O `rpy2` fica inteiramente dentro deste módulo: entra numpy, sai numpy, e
nenhuma outra parte do projeto sabe que existe R.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.cross_decomposition import PLSRegression

from tcc.arms.base import Budget, CVFolds
from tcc.arms.pls import PLSArm

# Faixa de candidatos declarada a priori no ADR 012, igual nos quatro
# conjuntos. A largura do intervalo varia com p, e isso é deliberado: o
# número de intervalos é o parâmetro ajustável, não a largura.
DEFAULT_INT_NUM_CANDIDATES = (10, 15, 20, 25, 30)


def _r():
    """Importa o mdatools sob demanda.

    Adiado para o momento da chamada, e não no topo do módulo, para que
    importar `tcc.arms.ipls` não exija um R instalado — quem não usa o
    braço não paga a dependência.
    """
    import rpy2.robjects as ro
    from rpy2.robjects import numpy2ri
    from rpy2.robjects.packages import importr

    # Namespace explícito no ADR 008: carregar mdatools e plsVarSel juntos
    # mascara nomes (pls::crossval sobre mdatools::crossval). `importr`
    # devolve o namespace do pacote, sem depender da ordem de library().
    return ro, numpy2ri, importr("mdatools")


def _segments_from_folds(n: int, cv_folds: CVFolds) -> np.ndarray:
    """Converte as folds injetadas no vetor de segmentos que o mdatools
    aceita (ADR 012): `crossval` devolve `as.matrix(cv)` quando recebe um
    vetor numérico de comprimento n, sem passar pelo gerador interno.

    Só é bem definido porque as folds de `evaluate` formam partição — todo
    registro é validação em exatamente um fold. A conferência é feita aqui
    em vez de ser assumida.
    """
    segments = np.zeros(n, dtype=int)
    for label, (_fold_train, fold_val) in enumerate(cv_folds, start=1):
        if np.any(segments[fold_val] != 0):
            raise ValueError("folds sobrepostas: não formam partição")
        segments[fold_val] = label
    if np.any(segments == 0):
        raise ValueError("folds não cobrem todas as linhas: não formam partição")
    return segments


def _select_intervals(
    X: np.ndarray,
    y: np.ndarray,
    segments: np.ndarray,
    int_num: int,
    glob_ncomp: int,
) -> tuple[set[int], int]:
    """Uma execução do `mdatools::ipls`.

    Devolve `(canais selecionados, ajustes consumidos)`. Índices
    convertidos de 1-based (R) para 0-based (Python) na saída.

    O segundo valor existe porque contar 1 por chamada tornaria o `n_fits`
    do iPLS incomparável com o do PLS — uma auditoria em 28/09/2026 mediu
    6 contra 101 do `pls_full`, com o iPLS gastando 30× mais tempo. O
    pipeline exige o contrário: "se o GA-PLS consumir 40× mais ajustes que
    o MLP, isso precisa aparecer na tabela".

    A contagem é ESTIMADA, e a base dela foi conferida em 28/09/2026: o
    `int.stat` traz **uma linha para o modelo global de espectro completo**
    (`n = 0`, `selected = FALSE`) seguida de uma linha por intervalo
    aceito. Ou seja, `nrow(int.stat) = 1 + intervalos selecionados`, e não
    "uma linha por iteração", como uma primeira versão deste comentário
    afirmava.

    A busca forward que seleciona `s` intervalos faz `s + 1` passadas —
    `s` que aceitam e uma final que não melhora —, e em cada passada avalia
    os intervalos ainda não escolhidos, cada um por CV sobre os segmentos.
    Como `nrow` também vale `s + 1`, usá-lo como número de passadas dá o
    resultado certo; a coincidência é registrada aqui porque o número
    depende do formato dessa tabela, e uma mudança nela quebraria a
    estimativa em silêncio.

    Declarada como estimativa, não como contagem exata: o interior do
    pacote não é instrumentado.
    """
    ro, numpy2ri, mdatools = _r()

    width = max(1, X.shape[1] // int_num)
    # Um PLS com mais componentes que variáveis no intervalo é degenerado;
    # com int.num alto os intervalos ficam estreitos, então o número de
    # componentes DENTRO do intervalo é limitado pela largura dele.
    int_ncomp = max(1, min(glob_ncomp, width))

    # Só a ENTRADA é convertida dentro do contexto. Chamar o ipls lá
    # dentro faria o retorno vir como `NamedList`, que não expõe `rx2` nem
    # acesso por nome — o objeto do R chega desmontado e sem os rótulos.
    # Convertendo só os argumentos, a chamada devolve um `ListVector` e os
    # campos saem por nome.
    with (ro.default_converter + numpy2ri.converter).context():
        conversion = ro.conversion.get_conversion()
        x_r = conversion.py2rpy(X)
        y_r = conversion.py2rpy(y.reshape(-1, 1))
        segments_r = conversion.py2rpy(segments.astype(float))

    model = mdatools.ipls(
        x_r,
        y_r,
        **{
            "glob.ncomp": glob_ncomp,
            "int.ncomp": int_ncomp,
            "int.num": int_num,
            "method": "forward",
            "cv": segments_r,
            "silent": True,
        },
    )
    selected = np.asarray(model.rx2("var.selected"), dtype=int)

    # Iterações da busca forward = linhas de int.stat. Na iteração k
    # (1-based) restam int_num - (k-1) intervalos candidatos, e cada um é
    # avaliado por CV sobre os segmentos.
    n_iterations = int(np.asarray(ro.r("nrow")(model.rx2("int.stat")))[0])
    n_segments = int(segments.max())
    n_fits = sum(
        max(1, int_num - k) * n_segments for k in range(n_iterations)
    )

    return {int(j) - 1 for j in selected}, n_fits


def _fit_pls(X: np.ndarray, y: np.ndarray, bands: set[int], n_components: int):
    """PLS do projeto sobre o subconjunto de bandas, com o número de
    componentes recortado pelo que o subconjunto suporta."""
    columns = np.sort(np.fromiter(bands, dtype=int))
    n_components = max(1, min(n_components, len(columns), X.shape[0] - 1))
    model = PLSRegression(n_components=n_components).fit(X[:, columns], y)
    return model, columns, n_components


@dataclass(frozen=True)
class _FittedIPLSArm:
    _model: PLSRegression
    _columns: np.ndarray
    _hyperparams: dict
    _rmse_cv: float
    _cv_selections: list[set[int]]

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.asarray(self._model.predict(X[:, self._columns])).ravel()

    @property
    def band_scores(self) -> np.ndarray | None:
        # iPLS devolve um conjunto, não um ranking contínuo: não há escore
        # por banda a reportar. O Estágio 4 usa `selection` para esses
        # métodos, e band_scores só para portas contínuas e VIP.
        return None

    @property
    def hyperparams(self) -> dict:
        return self._hyperparams

    @property
    def rmse_cv(self) -> float:
        return self._rmse_cv

    @property
    def cv_selections(self) -> list[set[int]] | None:
        return self._cv_selections

    @property
    def selection(self) -> set[int]:
        """Bandas do ajuste final, para o Estágio 4."""
        return {int(j) for j in self._columns}


class IPLSArm:
    """Braço A3: iPLS.

    `int_num=None` (padrão) escolhe o número de intervalos por validação
    cruzada nas folds injetadas, como o "ajuste justo" do pipeline exige.
    Um valor fixo pula a busca — modo usado pelo verificador anti-vazamento
    do ADR 011, que exige hiperparâmetro fixo para não confundir localidade
    da seleção com agregação da CV.

    A seleção é ANINHADA (ADR 012): dentro de cada fold, os intervalos são
    escolhidos só com `fold_train`. É mais caro que rodar o iPLS uma vez
    sobre o treino inteiro, e é justamente a diferença entre o benchmark
    ser válido ou ser o erro que o pipeline chama de mais comum da
    literatura de seleção em quimiometria.
    """

    def __init__(
        self,
        int_num: int | None = None,
        glob_ncomp: int | None = None,
        candidates: tuple[int, ...] = DEFAULT_INT_NUM_CANDIDATES,
    ):
        self._fixed_int_num = int_num
        self._fixed_glob_ncomp = glob_ncomp
        self._candidates = candidates
        parts = []
        if int_num is not None:
            parts.append(f"int_num={int_num}")
        if glob_ncomp is not None:
            parts.append(f"glob_ncomp={glob_ncomp}")
        self.name = "ipls" if not parts else f"ipls({', '.join(parts)})"

    def _global_ncomp(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        cv_folds: CVFolds,
        budget: Budget,
    ) -> int:
        """Número de componentes pela regra de um erro-padrão do `PLSArm`
        (ADR 012), e não pelo `ncomp.selcrit` do mdatools, que só oferece
        argmin e Wold. Mantém a regra de complexidade igual entre os
        braços.

        ATENÇÃO — este valor é buscado sobre TODO o `X_train`, agregando as
        folds, que é o que a validação cruzada faz e é legítimo. Mas ele
        entra em todas as execuções do iPLS, inclusive nas de cada fold:
        mudar uma linha de validação muda o `glob_ncomp` e, por tabela, a
        seleção de todos os folds. Por isso o verificador anti-vazamento do
        ADR 011 exige hiperparâmetro FIXO — e, neste braço, "fixo" quer
        dizer `int_num` **e** `glob_ncomp`, não só o primeiro.
        """
        if self._fixed_glob_ncomp is not None:
            return self._fixed_glob_ncomp
        n_components, _ = PLSArm()._search(X_train, y_train, cv_folds, budget)
        return n_components

    def _fold_selections(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        cv_folds: CVFolds,
        int_num: int,
        glob_ncomp: int,
        budget: Budget,
    ) -> list[set[int]]:
        """Seleção aninhada: um iPLS por fold, só sobre `fold_train`."""
        selections = []
        for index, (fold_train, _fold_val) in enumerate(cv_folds):
            inner_folds = _inner_folds(cv_folds, index)
            segments = _segments_from_folds(len(fold_train), inner_folds)
            bands, n_inner_fits = _select_intervals(
                X_train[fold_train],
                y_train[fold_train],
                segments,
                int_num,
                glob_ncomp,
            )
            selections.append(bands)
            budget.increment(n_inner_fits)
        return selections

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        cv_folds: CVFolds,
        rng_algo: np.random.Generator,
        budget: Budget,
    ) -> _FittedIPLSArm:
        glob_ncomp = self._global_ncomp(X_train, y_train, cv_folds, budget)

        if self._fixed_int_num is not None:
            int_num = self._fixed_int_num
            rmse_cv = float("nan")
            selections = self._fold_selections(
                X_train, y_train, cv_folds, int_num, glob_ncomp, budget
            )
        else:
            int_num, rmse_cv, selections = self._search(
                X_train, y_train, cv_folds, glob_ncomp, budget
            )

        segments = _segments_from_folds(len(y_train), cv_folds)
        final_bands, n_final_fits = _select_intervals(
            X_train, y_train, segments, int_num, glob_ncomp
        )
        budget.increment(n_final_fits)
        model, columns, n_components = _fit_pls(
            X_train, y_train, final_bands, glob_ncomp
        )

        return _FittedIPLSArm(
            _model=model,
            _columns=columns,
            _hyperparams={
                "int_num": int_num,
                "glob_ncomp": glob_ncomp,
                "n_components": n_components,
                "n_bands": len(columns),
            },
            _rmse_cv=rmse_cv,
            _cv_selections=selections,
        )

    def _search(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        cv_folds: CVFolds,
        glob_ncomp: int,
        budget: Budget,
    ) -> tuple[int, float, list[set[int]]]:
        """Escolhe `int_num` por CV aninhada, com a MESMA regra de um
        erro-padrão do `PLSArm` — critério de complexidade uniforme entre
        os braços.

        Para cada candidato: seleciona intervalos dentro de cada fold
        (só com `fold_train`), ajusta o PLS do projeto nessas bandas e
        pontua em `fold_val`. A seleção nunca enxerga a partição de
        validação, que é a armadilha central do Estágio 2.
        """
        mean_rmse = np.empty(len(self._candidates))
        se_rmse = np.empty(len(self._candidates))
        per_candidate: list[list[set[int]]] = []

        for i, int_num in enumerate(self._candidates):
            selections = self._fold_selections(
                X_train, y_train, cv_folds, int_num, glob_ncomp, budget
            )
            fold_rmses = []
            for (fold_train, fold_val), bands in zip(cv_folds, selections):
                model, columns, _ = _fit_pls(
                    X_train[fold_train], y_train[fold_train], bands, glob_ncomp
                )
                budget.increment()
                y_hat = np.asarray(model.predict(X_train[fold_val][:, columns])).ravel()
                fold_rmses.append(
                    float(np.sqrt(np.mean((y_train[fold_val] - y_hat) ** 2)))
                )

            fold_rmses = np.asarray(fold_rmses)
            mean_rmse[i] = fold_rmses.mean()
            se_rmse[i] = (
                fold_rmses.std(ddof=1) / np.sqrt(len(fold_rmses))
                if len(fold_rmses) > 1
                else 0.0
            )
            per_candidate.append(selections)

        i_min = int(np.argmin(mean_rmse))
        threshold = mean_rmse[i_min] + se_rmse[i_min]
        # Candidatos em ordem crescente: o primeiro dentro do limiar é o
        # MENOS intervalos, ou seja, o modelo mais parcimonioso ainda
        # indistinguível do melhor.
        i_chosen = int(np.argmax(mean_rmse <= threshold))
        return (
            self._candidates[i_chosen],
            float(mean_rmse[i_chosen]),
            per_candidate[i_chosen],
        )


def _inner_folds(cv_folds: CVFolds, index: int) -> CVFolds:
    """Folds para a CV que o próprio iPLS roda dentro do fold externo
    `index`, reindexadas para a posição dentro de `fold_train`.

    São os OUTROS blocos de validação do protocolo, e não uma partição
    nova. Isso resolve um problema que o contrato do `Arm` cria: o braço
    não recebe `dataset.groups`, então não teria como respeitar por conta
    própria a regra do ADR 009 — réplicas da mesma amostra física nunca em
    lados diferentes, nem entre folds da CV interna. Reaproveitando os
    blocos externos, a garantia é herdada de `_make_cv_folds`, sem o braço
    precisar conhecer os grupos.

    A primeira versão fatiava `arange(n)` em pedaços contíguos. No Tecator
    passava — só há 7 pares de réplicas e nenhum caía na fronteira —, mas
    numa auditoria com réplicas densas (o padrão do Mango e do bioprocess,
    2+ leituras por amostra) partia 664 grupos. Bug latente, invisível de
    fora do braço, encontrado em 28/09/2026.
    """
    fold_train = cv_folds[index][0]
    position = {int(row): i for i, row in enumerate(fold_train)}
    folds: CVFolds = []
    for other, (_fold_train, fold_val) in enumerate(cv_folds):
        if other == index:
            continue
        local_val = np.array(
            [position[int(v)] for v in fold_val if int(v) in position], dtype=int
        )
        if len(local_val) == 0:
            continue
        local_train = np.setdiff1d(np.arange(len(fold_train)), local_val)
        folds.append((local_train, local_val))
    return folds
