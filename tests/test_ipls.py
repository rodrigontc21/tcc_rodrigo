"""Braço A3 (iPLS via mdatools) — ADR 012.

Exigem R com o `mdatools` instalado, então são pulados onde a ponte não
existe. O restante da suíte continua rodando sem R.
"""

from __future__ import annotations

import numpy as np
import pytest

from tcc.arms.base import Budget, CVFolds

pytest.importorskip("rpy2.robjects", reason="rpy2 indisponível (ADR 008)")


def _mdatools_available() -> bool:
    """rpy2 instalado não garante R com o `mdatools`: são dependências
    distintas, e o pacote R vive fora do venv."""
    try:
        from rpy2.robjects.packages import importr

        importr("mdatools")
    except Exception:  # noqa: BLE001
        return False
    return True


pytestmark = pytest.mark.skipif(
    not _mdatools_available(), reason="pacote R mdatools indisponível (ADR 008)"
)

import tcc.arms.ipls as ipls_module  # noqa: E402
from tcc.arms.ipls import IPLSArm, _inner_folds, _segments_from_folds  # noqa: E402
from tcc.arms.pls import PLSArm  # noqa: E402
from tcc.protocol import _make_cv_folds  # noqa: E402
from tests.test_selection_leakage import (  # noqa: E402
    assert_selection_is_fold_local,
)

N_FOLDS = 3


class _IplsSpy:
    """Registra os argumentos de cada chamada a `mdatools::ipls` e delega
    ao pacote de verdade.

    Existe porque três invariantes do ADR 012 só são verificáveis no que
    atravessa a ponte para o R, e não na saída do braço: as folds
    injetadas (contra o risco do ADR 001), a localidade dessas folds
    (ADR 009) e o recorte de `int.ncomp` pela largura. Sem esta sonda, as
    três mutações correspondentes passam verdes — verificado em
    28/09/2026, numa vistoria independente.
    """

    def __init__(self, real):
        self._real = real
        self.calls: list[dict] = []

    def ipls(self, x, y, **kwargs):
        self.calls.append(dict(kwargs))
        return self._real.ipls(x, y, **kwargs)


@pytest.fixture
def ipls_spy(monkeypatch):
    real_ro, real_numpy2ri, real_mdatools = ipls_module._r()
    spy = _IplsSpy(real_mdatools)
    monkeypatch.setattr(
        ipls_module, "_r", lambda: (real_ro, real_numpy2ri, spy)
    )
    return spy


def _segments_of(call, ro) -> np.ndarray:
    """Vetor de segmentos que o braço passou em `cv`, de volta em numpy."""
    return np.asarray(ro.r("as.numeric")(call["cv"]), dtype=int)


@pytest.fixture(scope="module")
def spectral_problem():
    """Problema sintético com estrutura espectral: bandas informativas
    contíguas, como o iPLS espera encontrar (ele seleciona intervalos, não
    canais isolados). Pequeno de propósito — o que está sob teste é o
    contrato do braço, não a qualidade da seleção."""
    rng = np.random.default_rng(0)
    n, p = 80, 40
    X = np.cumsum(rng.normal(size=(n, p)) * 0.3, axis=1)  # espectros lisos
    y = X[:, 10:15].sum(axis=1) * 2.0 + 0.1 * rng.normal(size=n)

    folds: CVFolds = []
    for chunk in np.array_split(np.arange(n), N_FOLDS):
        folds.append((np.setdiff1d(np.arange(n), chunk), chunk))
    return X, y, folds


def test_fit_produces_selection_and_cv_selections(spectral_problem):
    X, y, folds = spectral_problem
    fitted = IPLSArm(int_num=5, glob_ncomp=3).fit(
        X, y, folds, np.random.default_rng(0), Budget()
    )

    assert len(fitted.cv_selections) == len(folds)
    for selection in fitted.cv_selections:
        assert selection, "seleção vazia"
        assert max(selection) < X.shape[1] and min(selection) >= 0
    assert fitted.selection
    assert fitted.hyperparams["int_num"] == 5
    assert fitted.predict(X).shape == (X.shape[0],)


def test_selection_is_fold_local(spectral_problem):
    """O que o ADR 011 foi escrito para permitir: o verificador
    anti-vazamento aplicado a um braço REAL, e não às sondas sintéticas.

    Os dois hiperparâmetros vão fixos — ver `test_fixed_glob_ncomp_...`,
    que explica por quê.

    A prova de que este teste não passa por construção está em
    `test_check_catches_ipls_that_sees_the_validation_fold`: o mesmo
    verificador, nos mesmos dados, reprova um iPLS que seleciona sobre
    todo o treino.
    """
    X, y, folds = spectral_problem
    assert_selection_is_fold_local(
        lambda: IPLSArm(int_num=5, glob_ncomp=3), X, y, folds
    )


class _LeakyIPLSArm(IPLSArm):
    """iPLS que seleciona os intervalos sobre o treino INTEIRO, em vez de
    dentro de cada fold — o erro que o pipeline chama de mais comum da
    literatura de seleção em quimiometria. Existe só para provar que o
    verificador o detecta."""

    name = "leaky_ipls"

    def _fold_selections(self, X_train, y_train, cv_folds, int_num, glob_ncomp, budget):
        from tcc.arms.ipls import _select_intervals, _segments_from_folds

        segments = _segments_from_folds(len(y_train), cv_folds)
        bands, n_fits, _ = _select_intervals(
            X_train, y_train, segments, int_num, glob_ncomp
        )
        budget.increment(n_fits)
        return [set(bands) for _ in cv_folds]


def test_check_catches_ipls_that_sees_the_validation_fold(spectral_problem):
    """A prova de que o verificador tem dentes CONTRA ESTE BRAÇO.

    Sem este teste, `test_selection_is_fold_local` acima poderia estar
    verde por construção — e esteve, até 28/09/2026, quando uma mutação
    mostrou que um iPLS deliberadamente vazado não era detectado.
    """
    X, y, folds = spectral_problem
    with pytest.raises(AssertionError, match="vazamento"):
        assert_selection_is_fold_local(
            lambda: _LeakyIPLSArm(int_num=5, glob_ncomp=3), X, y, folds
        )


def test_fixed_glob_ncomp_bypasses_the_search(spectral_problem):
    """Por que `glob_ncomp` é parâmetro — achado de 28/09.

    Em busca, o `glob_ncomp` sai da regra de um erro-padrão aplicada a
    TODO o `X_train`, agregando as folds, que é o que a validação cruzada
    legitimamente faz. Só que esse valor entra em todas as execuções do
    iPLS, inclusive nas de cada fold: mexer numa linha de validação pode
    mudar o `glob_ncomp` e, por tabela, a seleção daquele fold. O
    verificador do ADR 011 leria isso como vazamento, quando é agregação
    da CV — o falso positivo que aquele ADR previu ao exigir
    hiperparâmetro fixo.

    Foi o que aconteceu na primeira execução do verificador contra este
    braço, no Tecator: reprovou com só o `int_num` fixo e passou com os
    dois. O disparo depende dos dados — neste problema sintético a
    perturbação não chega a mudar a escolha —, então o que se testa aqui é
    o mecanismo, e não o sintoma: com `glob_ncomp` fixo, a busca não
    acontece, e é isso que corta o acoplamento.
    """
    X, y, folds = spectral_problem
    arm = IPLSArm(int_num=5, glob_ncomp=2)

    budget_fixed = Budget()
    assert arm._global_ncomp(X, y, folds, budget_fixed) == 2
    assert budget_fixed.n_fits == 0, "valor fixo não deve consumir orçamento"

    budget_search = Budget()
    searched = IPLSArm(int_num=5)._global_ncomp(X, y, folds, budget_search)
    assert budget_search.n_fits > 0, "a busca tem que aparecer no orçamento"
    assert searched >= 1


def test_inner_folds_never_split_a_replicate_group():
    """Regressão do bug achado na auditoria de 28/09/2026.

    O ADR 009 vale também dentro do braço: réplicas da mesma amostra
    física não podem ficar em folds diferentes, nem nas folds internas que
    o iPLS usa para pontuar intervalos. O contrato do `Arm` não entrega
    `dataset.groups`, então o braço não tem como respeitar a regra por
    conta própria — ele deriva as folds internas das externas, herdando a
    garantia de `_make_cv_folds`.

    A primeira versão fatiava `arange(n)` em pedaços contíguos. No Tecator
    passava, porque há só 7 pares de réplicas e nenhum caía na fronteira.
    Com réplicas densas — o padrão do Mango (em geral 2 leituras por
    fruto) e do bioprocess (toda amostra com 2+ espectros) — partia 664
    grupos, e o vazamento era invisível de fora do braço.
    """
    groups = np.random.default_rng(0).permutation(np.repeat(np.arange(100), 2))
    outer = _make_cv_folds(len(groups), 5, np.random.default_rng(0), groups)

    for index, (fold_train, _fold_val) in enumerate(outer):
        groups_in_fold = groups[fold_train]
        inner = _inner_folds(outer, index)
        assert inner, "folds internas vazias"
        for inner_train, inner_val in inner:
            shared = set(groups_in_fold[inner_train]) & set(groups_in_fold[inner_val])
            assert not shared, f"fold externo {index}: {len(shared)} grupos partidos"


def test_budget_reflects_the_real_cost_of_the_search():
    """Regressão do segundo achado da auditoria de 28/09/2026.

    Contar 1 ajuste por chamada do `ipls` dava `n_fits = 6` contra 101 do
    `pls_full`, com o iPLS gastando ~25× mais tempo. O `n_fits` existe
    justamente para tornar o orçamento auditável entre braços — com a
    contagem antiga, a tabela de custo do manuscrito diria o oposto da
    verdade.
    """
    rng = np.random.default_rng(1)
    n, p = 60, 30
    X = np.cumsum(rng.normal(size=(n, p)) * 0.3, axis=1)
    y = X[:, 5:10].sum(axis=1) + 0.1 * rng.normal(size=n)
    folds = [
        (np.setdiff1d(np.arange(n), chunk), chunk)
        for chunk in np.array_split(np.arange(n), 3)
    ]

    budget = Budget()
    IPLSArm(int_num=5, glob_ncomp=2).fit(X, y, folds, np.random.default_rng(0), budget)

    # 4 execuções do ipls (3 folds + final), cada uma avaliando vários
    # intervalos por vários segmentos: a ordem de grandeza é dezenas, não
    # unidades.
    assert budget.n_fits > 4 * len(folds), f"n_fits={budget.n_fits} baixo demais"


def test_folds_of_the_protocol_are_injected_into_mdatools(ipls_spy):
    """O `cv` que chega ao mdatools são as folds do protocolo, e não as do
    pacote.

    Sem `cv`, o `mdatools::ipls` usa o default `list("ven", 10)` — dez
    segmentos venezianos construídos por ele. Seria exatamente o risco que
    o ADR 001 registrou e que o ADR 012 afirma ter fechado, e a saída do
    braço não denuncia: as bandas selecionadas continuam plausíveis.
    Verificado em 28/09/2026 que remover a injeção não quebrava teste
    nenhum.
    """
    import rpy2.robjects as ro

    groups = np.random.default_rng(3).permutation(np.repeat(np.arange(40), 2))
    n = len(groups)
    rng = np.random.default_rng(4)
    X = np.cumsum(rng.normal(size=(n, 40)) * 0.3, axis=1)
    y = X[:, 10:15].sum(axis=1) + 0.1 * rng.normal(size=n)
    folds = _make_cv_folds(n, 4, np.random.default_rng(0), groups)

    IPLSArm(int_num=5, glob_ncomp=2).fit(
        X, y, folds, np.random.default_rng(0), Budget()
    )

    assert ipls_spy.calls, "nenhuma chamada ao ipls foi registrada"
    for call in ipls_spy.calls:
        assert "cv" in call, "o braço deixou o mdatools escolher as folds"

    # A última chamada é o ajuste final, sobre o treino inteiro: os
    # segmentos têm que ser exatamente os das folds injetadas.
    final = _segments_of(ipls_spy.calls[-1], ro)
    np.testing.assert_array_equal(final, _segments_from_folds(n, folds))


def test_inner_folds_reaching_r_never_split_a_group(ipls_spy):
    """O ADR 009 valendo no que de fato atravessa a ponte.

    O teste `test_inner_folds_never_split_a_replicate_group` chama o helper
    `_inner_folds` diretamente, então não pega uma mutação escrita dentro
    do braço. Este aqui audita os segmentos que chegaram ao R em cada fold
    externo.
    """
    import rpy2.robjects as ro

    groups = np.random.default_rng(5).permutation(np.repeat(np.arange(40), 2))
    n = len(groups)
    rng = np.random.default_rng(6)
    X = np.cumsum(rng.normal(size=(n, 40)) * 0.3, axis=1)
    y = X[:, 10:15].sum(axis=1) + 0.1 * rng.normal(size=n)
    folds = _make_cv_folds(n, 4, np.random.default_rng(0), groups)

    IPLSArm(int_num=5, glob_ncomp=2).fit(
        X, y, folds, np.random.default_rng(0), Budget()
    )

    # Uma chamada por fold externo, mais o ajuste final.
    assert len(ipls_spy.calls) == len(folds) + 1
    for index, call in enumerate(ipls_spy.calls[:-1]):
        segments = _segments_of(call, ro)
        groups_in_fold = groups[folds[index][0]]
        assert len(segments) == len(groups_in_fold)
        for label in np.unique(segments):
            in_segment = set(groups_in_fold[segments == label])
            out_segment = set(groups_in_fold[segments != label])
            assert not (in_segment & out_segment), (
                f"fold externo {index}: grupo dos dois lados do segmento {label}"
            )


def test_int_ncomp_is_capped_by_the_interval_width(ipls_spy):
    """O recorte declarado no ADR 012 chega ao pacote.

    `int.ncomp = min(glob.ncomp, largura)`: um PLS com mais componentes que
    variáveis no intervalo é degenerado. Sem este teste, remover o recorte
    não quebrava nada."""
    rng = np.random.default_rng(7)
    n, p = 60, 30
    X = np.cumsum(rng.normal(size=(n, p)) * 0.3, axis=1)
    y = X[:, 5:10].sum(axis=1) + 0.1 * rng.normal(size=n)
    folds = [
        (np.setdiff1d(np.arange(n), c), c) for c in np.array_split(np.arange(n), 3)
    ]

    # largura = 30 // 15 = 2, abaixo do glob_ncomp pedido
    IPLSArm(int_num=15, glob_ncomp=6).fit(
        X, y, folds, np.random.default_rng(0), Budget()
    )

    for call in ipls_spy.calls:
        assert call["int.ncomp"] == min(6, p // 15), call["int.ncomp"]
        assert call["glob.ncomp"] == 6


def test_final_model_uses_the_selection_of_the_whole_training_set():
    """O modelo final é ajustado na seleção feita sobre TODO o treino, e
    não na de algum fold.

    As seleções por fold servem à auditoria (ADR 011) e à escolha de
    `int_num`; o modelo entregue é outro objeto.

    O cenário é fixado na semente 3 porque precisa DISCRIMINAR: dois blocos
    informativos de força parecida (coeficientes 1,00 e 0,95) deixam a
    escolha instável entre subconjuntos de linhas, e aí a seleção do fold 0
    difere da do treino inteiro. No fixture anterior as duas coincidiam, e
    trocar uma pela outra passava verde — apontado por vistoria
    independente em 28/09/2026 e confirmado por mutação.
    """
    from tcc.arms.ipls import _select_intervals

    rng = np.random.default_rng(3)
    n, p = 60, 40
    X = np.cumsum(rng.normal(size=(n, p)) * 0.3, axis=1)
    y = (
        X[:, 8:14].sum(axis=1)
        + 0.95 * X[:, 24:30].sum(axis=1)
        + 0.8 * rng.normal(size=n)
    )
    folds = [
        (np.setdiff1d(np.arange(n), c), c) for c in np.array_split(np.arange(n), 3)
    ]

    whole, _, _ = _select_intervals(X, y, _segments_from_folds(n, folds), 5, 3)
    fitted = IPLSArm(int_num=5, glob_ncomp=3).fit(
        X, y, folds, np.random.default_rng(0), Budget()
    )

    assert fitted.cv_selections[0] != whole, (
        "cenário não discrimina: a seleção do fold 0 é igual à do treino inteiro"
    )
    assert fitted.selection == whole


def test_searched_glob_ncomp_is_the_one_se_value(spectral_problem):
    """Quando `glob_ncomp` não é fixado, o valor usado é o que a regra de um
    erro-padrão do `PLSArm` devolve — e não um default qualquer. Ignorar o
    resultado da busca não quebrava nada."""
    X, y, folds = spectral_problem
    expected, _ = PLSArm()._search(X, y, folds, Budget())

    fitted = IPLSArm(int_num=5).fit(X, y, folds, np.random.default_rng(0), Budget())

    assert fitted.hyperparams["glob_ncomp"] == expected


def test_budget_counts_the_cv_segments():
    """O `n_fits` conta os segmentos de CV, e não só os intervalos.

    Cada intervalo candidato é avaliado uma vez por segmento, então dobrar
    os segmentos dobra os ajustes. O teste é feito direto em
    `_select_intervals`, com os MESMOS dados e o mesmo `int_num`, variando
    só o número de segmentos — comparar dois números de folds externas não
    serve, porque aí muda também a quantidade de chamadas ao iPLS, e a
    contagem cresce mesmo sem o fator `n_segments`. Foi assim que a mutação
    escapou na primeira tentativa, em 28/09/2026.
    """
    from tcc.arms.ipls import _select_intervals

    rng = np.random.default_rng(8)
    n, p = 72, 30
    X = np.cumsum(rng.normal(size=(n, p)) * 0.3, axis=1)
    y = X[:, 5:10].sum(axis=1) + 0.1 * rng.normal(size=n)

    counts = {}
    for n_segments in (2, 6):
        segments = np.repeat(np.arange(1, n_segments + 1), n // n_segments)
        _, n_fits, _ = _select_intervals(X, y, segments, 5, 2)
        counts[n_segments] = n_fits

    assert counts[6] > counts[2], counts
    # a razão tem que acompanhar a dos segmentos, não ser constante
    assert counts[6] >= 2 * counts[2], counts


def test_int_num_uses_the_one_standard_error_rule_not_argmin():
    """A escolha de `int_num` segue a regra de um erro-padrão, não o argmin
    puro do erro de CV.

    O cenário é fixado porque precisa DISCRIMINAR as duas regras: com a
    semente 9 e os candidatos (4, 8, 12), o argmin cai em 12 e a regra de
    um erro-padrão em 4. Sem essa verificação, trocar a regra por argmin
    passava verde — apontado por vistoria independente em 28/09/2026.

    Isto testa qual regra o código aplica, e NÃO que ela seja a regra
    certa. Ela tem a parcimônia invertida — menos intervalos retêm mais
    bandas —, o que está declarado no ADR 012 e é a pergunta 12 à
    orientação. Se a resposta mudar a regra, este teste muda junto.
    """
    from tcc.arms.ipls import _fit_pls, _select_intervals

    candidates = (4, 8, 12)
    rng = np.random.default_rng(9)
    n, p = 70, 48
    X = np.cumsum(rng.normal(size=(n, p)) * 0.3, axis=1)
    y = X[:, 12:18].sum(axis=1) + 0.4 * rng.normal(size=n)
    folds = [
        (np.setdiff1d(np.arange(n), c), c) for c in np.array_split(np.arange(n), 3)
    ]

    # Reimplementa o argmin puro sobre a MESMA curva, como referência —
    # mesmo padrão de `_argmin_choice` em tests/test_pls.py.
    means = []
    for int_num in candidates:
        fold_rmses = []
        for index, (fold_train, fold_val) in enumerate(folds):
            segments = _segments_from_folds(
                len(fold_train), _inner_folds(folds, index)
            )
            bands, _, _ = _select_intervals(
                X[fold_train], y[fold_train], segments, int_num, 3
            )
            model, columns, _ = _fit_pls(X[fold_train], y[fold_train], bands, 3)
            y_hat = np.asarray(model.predict(X[fold_val][:, columns])).ravel()
            fold_rmses.append(float(np.sqrt(np.mean((y[fold_val] - y_hat) ** 2))))
        means.append(float(np.mean(fold_rmses)))
    argmin_choice = candidates[int(np.argmin(means))]

    fitted = IPLSArm(glob_ncomp=3, candidates=candidates).fit(
        X, y, folds, np.random.default_rng(0), Budget()
    )
    chosen = fitted.hyperparams["int_num"]

    assert argmin_choice != chosen, (
        f"cenário não discrimina: argmin e regra escolheram {chosen}"
    )
    assert chosen == min(candidates), (
        f"a regra de um erro-padrão deveria ficar com o menor candidato "
        f"dentro do limiar; escolheu {chosen}"
    )


def test_hyperparams_record_the_executed_number_of_intervals():
    """O `int.num` pedido não é sempre o executado, e o `hyperparams` tem
    que registrar o que rodou.

    O mdatools converte o número de intervalos em largura, arredonda, e
    recalcula quantos cabem em `p`. Com p = 100 e 15 pedidos, saem 14. Se
    o `hyperparams` guardasse só o pedido, ele descreveria um experimento
    que não aconteceu — e a faixa declarada no ADR 012 não seria a faixa
    avaliada. Apontado por vistoria independente em 28/09/2026.
    """
    rng = np.random.default_rng(11)
    n, p = 60, 100
    X = np.cumsum(rng.normal(size=(n, p)) * 0.3, axis=1)
    y = X[:, 20:26].sum(axis=1) + 0.1 * rng.normal(size=n)
    folds = [
        (np.setdiff1d(np.arange(n), c), c) for c in np.array_split(np.arange(n), 3)
    ]

    fitted = IPLSArm(int_num=15, glob_ncomp=3).fit(
        X, y, folds, np.random.default_rng(0), Budget()
    )

    assert fitted.hyperparams["int_num"] == 15
    assert fitted.hyperparams["int_num_executed"] == 14, (
        "o cenário deixou de discriminar: pedido e executado coincidiram"
    )


def test_segments_require_a_partition():
    """As folds viram vetor de segmentos para o mdatools, e isso só é bem
    definido se elas particionarem as linhas (ADR 012)."""
    overlapping: CVFolds = [
        (np.array([2, 3]), np.array([0, 1])),
        (np.array([0, 3]), np.array([1, 2])),
    ]
    with pytest.raises(ValueError, match="sobrepostas"):
        _segments_from_folds(4, overlapping)

    incomplete: CVFolds = [(np.array([1, 2, 3]), np.array([0]))]
    with pytest.raises(ValueError, match="não cobrem"):
        _segments_from_folds(4, incomplete)


def test_search_picks_a_candidate_and_reports_cost(spectral_problem):
    """Com `int_num` em busca, o braço escolhe um dos candidatos
    declarados no ADR 012 e o orçamento reflete o custo da seleção
    aninhada — que é o ponto do `n_fits` no pipeline."""
    X, y, folds = spectral_problem
    budget = Budget()
    fitted = IPLSArm(glob_ncomp=3, candidates=(4, 8)).fit(
        X, y, folds, np.random.default_rng(0), budget
    )

    assert fitted.hyperparams["int_num"] in (4, 8)
    assert np.isfinite(fitted.rmse_cv)
    # 2 candidatos x 3 folds (seleção) + 2 x 3 (ajuste) + 1 final
    assert budget.n_fits >= 2 * len(folds) * 2 + 1
