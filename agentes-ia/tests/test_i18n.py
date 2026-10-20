import string

import pytest

from suite.bipilot.strings import STRINGS as BI
from suite.datapilot.strings import STRINGS as DP
from suite.docpilot.strings import STRINGS as DOC
from suite.fraudpilot import logic as fraud
from suite.fraudpilot.strings import LETTERS
from suite.fraudpilot.strings import STRINGS as FR
from suite.icepilot.strings import STRINGS as ICE
from suite.i18n import COMMON, LANGS, Translator
from suite.slidepilot.strings import SAMPLE_OUTLINE
from suite.slidepilot.strings import STRINGS as SL

TABLES = {"common": COMMON, "datapilot": DP, "bipilot": BI, "docpilot": DOC, "slidepilot": SL, "fraudpilot": FR,
          "icepilot": ICE}


def fields(text):
    return {f for _, f, _, _ in string.Formatter().parse(text) if f}


@pytest.mark.parametrize("name", TABLES)
def test_every_key_has_three_languages_with_same_placeholders(name):
    for key, entry in TABLES[name].items():
        assert isinstance(entry, tuple) and len(entry) == 3, key
        assert all(isinstance(t, str) and t.strip() for t in entry), key
        if "{{" not in entry[0]:
            assert fields(entry[0]) == fields(entry[1]) == fields(entry[2]), key


def test_app_tables_do_not_shadow_common_keys():
    for name, table in TABLES.items():
        if name != "common":
            assert not set(table) & set(COMMON), name


def test_fraud_dynamic_keys_exist():
    t = Translator(COMMON, FR)
    keys = [f"typ_{x}" for x in fraud.TYPOLOGIES] + [f"st_{x}" for x in fraud.STATUSES]
    keys += [f"prod_{x}" for x in fraud.PRODUCTS] + [f"ch_{x}" for x in fraud.CHANNELS]
    keys += [f"ind_{x}" for x in fraud.INDICATORS] + [f"m_{x}" for x in fraud.FIELDS]
    keys += [k for v in fraud.ACTIONS.values() for k in v] + [k for v in fraud.DOCUMENTS.values() for k in v]
    keys += ["act_police", "doc_police_attached", "prio_high", "prio_medium", "prio_low"]
    for key in keys:
        t(key)
    assert not t.missing


def test_fraud_flags_and_letters():
    claim = fraud.new_claim()
    claim.update(amount=50, received="2026-10-01", txn_date="2026-01-01", prior_claims=3)
    claim["indicators"].update(card_in_possession=True, card_lost_stolen=True, new_account=True,
                               shared_credentials=True, recognizes_merchant=True)
    t = Translator(COMMON, FR)
    for key, params in fraud.evaluate(claim)["flags"]:
        t(key, **params)
    assert not t.missing
    for kind, by_lang in LETTERS.items():
        assert set(by_lang) == set(LANGS), kind
        base = fields(by_lang["es"])
        for lang in LANGS:
            assert fields(by_lang[lang]) == base, (kind, lang)


def test_sample_outlines_in_three_languages():
    assert set(SAMPLE_OUTLINE) == set(LANGS)
