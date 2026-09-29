"""Teste anti-vazamento da seleção de variáveis (ADR 011).

A armadilha central do Estágio 2, nas palavras do pipeline: "seleção de
variáveis dentro da validação cruzada, nunca antes dela. Selecionar
bandas usando todo o conjunto de treino e depois validar é vazamento, e é
o erro mais comum na literatura de seleção em quimiometria. Escreva um
teste que falhe se a seleção enxergar a partição de validação."

O verificador aqui é `assert_selection_is_fold_local`, e a prova de que
ele tem dentes são as duas sondas: `_HonestSelectorArm`, que escolhe
bandas só com as linhas de `fold_train`, e `_LeakySelectorArm`, idêntica
exceto por olhar o treino inteiro. Um teste afirma que o verificador
aprova a primeira; outro, que reprova a segunda. Sem a segunda, este
seria mais um invariante testado com braço insensível ao mecanismo — o
padrão de falha registrado no DIARIO em 25/08 e 28/08.

Quando iPLS, CARS, GA-PLS e VIP existirem, cada um passa por
`assert_selection_is_fold_local` com o hiperparâmetro fixado.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pytest

from tcc.arms.base import Budget, CVFolds

# Banda em que a perturbação injeta correlação espúria. É ruído puro nos
# dados originais, então só entra no topo do ranking de quem olhar as
# linhas de validação.
SPURIOUS_BAND = 19
N_SELECTED = 3


def _top_k_by_correlation(X: np.ndarray, y: np.ndarray, k: int) -> set[int]:
    """Seleção-brinquedo: as k bandas de maior |correlação| com y.

    Não pretende ser um método de quimiometria — serve para que a sonda
    tenha uma regra de seleção determinística e sensível às linhas que
    recebe, que é o que o verificador precisa exercitar.
    """
    y_centered = y - y.mean()
    X_centered = X - X.mean(axis=0)
    denominator = np.linalg.norm(X_centered, axis=0) * np.linalg.norm(y_centered)
    with np.errstate(invalid="ignore", divide="ignore"):
        correlation = np.abs(X_centered.T @ y_centered / denominator)
    correlation = np.nan_to_num(correlation)
    return set(np.argsort(-correlation)[:k].tolist())


@dataclass(frozen=True)
class _FittedSelector:
    _mean: float
    _cv_selections: list[set[int]]

    def predict(self, X: np.ndarray) -> np.ndarray:
        # A qualidade da predição é irrelevante aqui: o que está sob teste
        # é de onde vieram as bandas, não o quanto o modelo acerta.
        return np.full(X.shape[0], self._mean)

    @property
    def band_scores(self) -> np.ndarray | None:
        return None

    @property
    def hyperparams(self) -> dict:
        return {"k": N_SELECTED}

    @property
    def rmse_cv(self) -> float:
        return float("nan")

    @property
    def cv_selections(self) -> list[set[int]] | None:
        return self._cv_selections


@dataclass
class _HonestSelectorArm:
    """Seleciona dentro de cada fold usando SÓ as linhas de `fold_train`."""

    name: str = "honest_selector"
    k: int = N_SELECTED

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        cv_folds: CVFolds,
        rng_algo: np.random.Generator,
        budget: Budget,
    ) -> _FittedSelector:
        selections = []
        for fold_train, _fold_val in cv_folds:
            selections.append(
                _top_k_by_correlation(X_train[fold_train], y_train[fold_train], self.k)
            )
            budget.increment()
        return _FittedSelector(float(np.mean(y_train)), selections)


@dataclass
class _LeakySelectorArm:
    """Idêntica à honesta, exceto por selecionar sobre o treino INTEIRO.

    É o erro que o pipeline descreve como o mais comum da literatura:
    escolher as bandas uma vez, com todos os dados de treino, e só depois
    validar. A seleção de cada fold passa a depender das linhas de
    validação daquele fold.
    """

    name: str = "leaky_selector"
    k: int = N_SELECTED

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        cv_folds: CVFolds,
        rng_algo: np.random.Generator,
        budget: Budget,
    ) -> _FittedSelector:
        leaked = _top_k_by_correlation(X_train, y_train, self.k)
        budget.increment()
        return _FittedSelector(float(np.mean(y_train)), [set(leaked) for _ in cv_folds])


def assert_selection_is_fold_local(
    make_arm,
    X_train: np.ndarray,
    y_train: np.ndarray,
    cv_folds: CVFolds,
    seed_algo: int = 0,
    n_spurious_bands: int = 1,
) -> None:
    """Falha se a seleção de algum fold enxergar a partição de validação.

    Para cada fold `i`, perturba as linhas de `fold_val[i]` e reajusta —
    arruinando as bandas que aquele fold havia escolhido e injetando
    correlação espúria numa banda de ruído. A seleção do fold `i` tem que
    sair idêntica:
    aquelas linhas não são treino dele. As seleções dos demais folds mudam
    — e devem mudar, porque para eles aquelas linhas são treino.

    `make_arm` é uma fábrica sem argumentos, e o hiperparâmetro tem que
    estar FIXO nela. Com busca ativa, o candidato escolhido depende de
    todas as folds, e a perturbação poderia trocá-lo — mudando a seleção
    do fold `i` por agregação da CV, não por vazamento (ADR 011).

    A perturbação tem duas partes, e a que faz o trabalho é a **dirigida**:
    as bandas que o fold escolheu são arruinadas nas linhas de validação
    dele. `n_spurious_bands` controla só a parte complementar — quantas
    bandas de ruído contíguas a partir de `SPURIOUS_BAND` recebem sinal
    espúrio —, e o default de uma banda basta em todos os casos testados
    até aqui, inclusive para métodos que selecionam intervalos inteiros.

    Histórico, porque a sequência é instrutiva. A primeira versão do
    verificador tinha só a parte espúria, com uma banda. Com o `IPLSArm`
    selecionando deliberadamente sobre todo o `X_train` — o vazamento que
    o Estágio 2 proíbe — a suíte inteira continuava verde: o iPLS escolhe
    intervalos, e uma banda perturbada dentro de um intervalo perdedor não
    o faz vencer. Alargar a perturbação para cobrir um intervalo inteiro
    **também não resolveu**: uma perturbação que alcança um terço das
    linhas não faz um intervalo ruim superar um bom. O que resolveu foi
    inverter a ideia — em vez de promover um perdedor, destruir o
    vencedor. Tudo em 28/09/2026.
    """

    def fit(X, y):
        return make_arm().fit(X, y, cv_folds, np.random.default_rng(seed_algo), Budget())

    baseline = fit(X_train, y_train).cv_selections
    if baseline is None:
        raise AssertionError(
            "braço sem cv_selections: não há o que auditar. Braços com "
            "seleção têm que preencher o campo (ADR 011)."
        )
    if len(baseline) != len(cv_folds):
        raise AssertionError(
            f"cv_selections tem {len(baseline)} entradas para "
            f"{len(cv_folds)} folds injetadas: o braço não usou as folds "
            f"que recebeu (ADR 001)."
        )

    rng = np.random.default_rng(seed_algo)
    for i, (_fold_train, fold_val) in enumerate(cv_folds):
        X_perturbed = X_train.copy()

        # Perturbação DIRIGIDA: arruína, só nas linhas de validação deste
        # fold, exatamente as bandas que ele escolheu. Quem enxerga essas
        # linhas passa a ver como ruidosas as bandas de que mais gostava e
        # troca de escolha; quem não as enxerga não tem como notar.
        #
        # É mais sensível que injetar sinal espúrio numa banda qualquer, e
        # funciona em qualquer granularidade — banda a banda ou por
        # intervalos inteiros, como o iPLS. Destruir o que já vence é mais
        # fácil que promover um perdedor: uma perturbação que alcança só
        # parte das linhas raramente faz um intervalo ruim superar um bom,
        # mas basta para estragar o bom.
        chosen = np.fromiter(baseline[i], dtype=int)
        X_perturbed[np.ix_(fold_val, chosen)] = 50.0 * rng.normal(
            size=(len(fold_val), len(chosen))
        )
        # Além disso, torna atraente uma banda que era ruído, para o caso
        # de um método que não reaja à degradação e sim à competição.
        spurious = np.arange(
            SPURIOUS_BAND, min(SPURIOUS_BAND + n_spurious_bands, X_train.shape[1])
        )
        spurious = np.setdiff1d(spurious, chosen)
        if len(spurious):
            X_perturbed[np.ix_(fold_val, spurious)] = y_train[fold_val, None] * 50.0

        perturbed = fit(X_perturbed, y_train).cv_selections
        assert perturbed[i] == baseline[i], (
            f"fold {i}: a seleção mudou quando as linhas de validação "
            f"foram perturbadas ({sorted(baseline[i])} -> "
            f"{sorted(perturbed[i])}). A seleção enxergou a partição de "
            f"validação — vazamento (Estágio 2 do pipeline)."
        )


@pytest.fixture
def selection_problem():
    """Dados sintéticos com exatamente `N_SELECTED` bandas informativas.

    O número de bandas informativas é igual a k de propósito: assim o
    top-k sobre dados limpos é sempre {0, 1, 2}, em qualquer fold e em
    qualquer subconjunto de linhas. Com menos bandas informativas que k,
    as vagas restantes seriam preenchidas por ruído e variariam de fold
    para fold — instabilidade que não é vazamento e que confundiria a
    leitura do verificador.

    A banda SPURIOUS_BAND é ruído aqui, e é nela que a perturbação injeta
    a correlação espúria.

    As colunas são ortogonalizadas (QR) antes de montar o alvo. Sem isso,
    a colinearidade amostral entre colunas "independentes" desloca as
    correlações de forma imprevisível: numa primeira versão deste fixture
    a banda 2 saiu com |r| = 0,03 apesar do coeficiente 1,2, e uma banda
    de ruído ocupou o lugar dela no top-3. Com colunas ortogonais,
    |r_j| = |coef_j| / ||y|| é previsível e não depende da sorte da
    semente: ~0,80, ~0,52 e ~0,31 para as três informativas, contra ~0,03
    do ruído.

    A parte espúria da perturbação alcança só as linhas de validação de um
    fold, e por isso sozinha nem sempre desloca uma banda informativa — foi
    o que levou o verificador a passar por construção contra o iPLS. Quem
    faz o trabalho é a parte dirigida, que arruína as bandas escolhidas; a
    espúria ficou como reforço.
    """
    rng = np.random.default_rng(0)
    n, p = 100, 20
    X, _ = np.linalg.qr(rng.normal(size=(n, p)))
    X *= np.sqrt(n)
    y = 3.0 * X[:, 0] - 2.0 * X[:, 1] + 1.2 * X[:, 2] + 0.3 * rng.normal(size=n)

    permutation = rng.permutation(n)
    folds: CVFolds = []
    for chunk in np.array_split(permutation, 5):
        val_idx = np.sort(chunk)
        train_idx = np.sort(np.setdiff1d(np.arange(n), val_idx))
        folds.append((train_idx, val_idx))

    # A premissa do fixture falha alto, aqui, e não de forma obscura lá
    # dentro de um teste: sobre dados limpos o top-k é exatamente o
    # conjunto das bandas informativas.
    assert _top_k_by_correlation(X, y, N_SELECTED) == set(range(N_SELECTED))
    return X, y, folds


def test_honest_selector_passes_the_check(selection_problem):
    X, y, folds = selection_problem
    assert_selection_is_fold_local(_HonestSelectorArm, X, y, folds)


def test_check_catches_selector_that_sees_the_validation_fold(selection_problem):
    """A prova de que o verificador tem dentes.

    Sem este teste, `assert_selection_is_fold_local` poderia estar
    passando por construção — exatamente o achado crítico de 25/08, em
    que um invariante era testado com um braço incapaz de violá-lo.
    """
    X, y, folds = selection_problem
    with pytest.raises(AssertionError, match="vazamento"):
        assert_selection_is_fold_local(_LeakySelectorArm, X, y, folds)


def test_spurious_band_is_absent_before_the_perturbation(selection_problem):
    """Controle que dá sentido ao verificador: sobre dados limpos, NENHUMA
    das duas sondas escolhe `SPURIOUS_BAND`, em fold nenhum.

    É o que torna a leitura do teste anterior inequívoca. Se a banda
    espúria já aparecesse antes da perturbação, o verificador poderia
    estar pegando instabilidade da própria seleção em vez de vazamento.
    Como ela não aparece, vê-la surgir depois da perturbação só pode vir
    de olhar as linhas de validação.

    Sobre dados limpos as duas sondas concordam integralmente: as bandas
    informativas são as mesmas vistas de qualquer subconjunto de linhas.
    Elas diferem apenas em de onde olharam, que é exatamente o que o
    verificador mede.
    """
    X, y, folds = selection_problem
    rng = np.random.default_rng(0)
    honest = _HonestSelectorArm().fit(X, y, folds, rng, Budget()).cv_selections
    leaky = _LeakySelectorArm().fit(X, y, folds, rng, Budget()).cv_selections

    assert honest == leaky
    for selection in honest + leaky:
        assert selection == set(range(N_SELECTED))
        assert SPURIOUS_BAND not in selection


def test_arm_that_ignores_injected_folds_is_rejected(selection_problem):
    """Contraparte do achado do ADR 001: um braço que devolve um número de
    seleções diferente do número de folds injetadas não passa."""
    X, y, folds = selection_problem

    class _WrongFoldCountArm(_HonestSelectorArm):
        # `name` não é redeclarado aqui de propósito: `_HonestSelectorArm`
        # é dataclass, e o `__init__` gerado sobrescreveria uma anotação
        # de classe na instância — o atributo pareceria definido e não
        # estaria. Renomear exigiria repetir o campo no __init__, e o
        # nome não importa para este teste.
        def fit(self, X_train, y_train, cv_folds, rng_algo, budget):
            # Constrói as próprias folds (3) em vez de usar as 5 injetadas
            own_folds = [
                (np.arange(len(y_train)), np.arange(0)) for _ in range(3)
            ]
            return super().fit(X_train, y_train, own_folds, rng_algo, budget)

    with pytest.raises(AssertionError, match="não usou as folds"):
        assert_selection_is_fold_local(_WrongFoldCountArm, X, y, folds)
