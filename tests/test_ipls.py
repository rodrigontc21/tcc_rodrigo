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

from tcc.arms.ipls import IPLSArm, _inner_folds, _segments_from_folds  # noqa: E402
from tcc.protocol import _make_cv_folds  # noqa: E402
from tests.test_selection_leakage import (  # noqa: E402
    assert_selection_is_fold_local,
)

N_FOLDS = 3


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

    `n_spurious_bands` cobre um intervalo INTEIRO (p=40 ÷ int_num=5 = 8
    bandas). Com a perturbação de uma banda só, este teste passava por
    construção: o iPLS seleciona intervalos, e uma banda perturbada dentro
    de um intervalo perdedor não o faz vencer. Ver
    `test_check_catches_ipls_that_sees_the_validation_fold`, que é a prova
    de que agora ele tem dentes.
    """
    X, y, folds = spectral_problem
    assert_selection_is_fold_local(
        lambda: IPLSArm(int_num=5, glob_ncomp=3),
        X,
        y,
        folds,
        n_spurious_bands=X.shape[1] // 5,
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
        bands, n_fits = _select_intervals(
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
            lambda: _LeakyIPLSArm(int_num=5, glob_ncomp=3),
            X,
            y,
            folds,
            n_spurious_bands=X.shape[1] // 5,
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
