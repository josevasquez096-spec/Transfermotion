import re
import string
from pathlib import Path

import pytest

from suite.bipilot.strings import STRINGS as BI
from suite.datapilot.strings import STRINGS as DP
from suite.docpilot.strings import STRINGS as DOC
from suite.fraudpilot import logic as fraud
from suite.fraudpilot.strings import LETTERS
from suite.fraudpilot.strings import STRINGS as FR
from suite.icepilot.strings import STRINGS as ICE
from suite.i18n import COMMON, LANGS, Translator
from suite.mailpilot import analysis as mp_analysis
from suite.mailpilot import app as mp_app
from suite.mailpilot import assist as mp_assist
from suite.mailpilot import backend_base, backend_demo, backend_outlook, model, phrases, widgets
from suite.mailpilot import detectors as mp_detectors
from suite.mailpilot import english as mp_english
from suite.mailpilot import query as mp_query
from suite.mailpilot import rules as mp_rules
from suite.mailpilot.strings import HELP as MP_HELP
from suite.mailpilot.strings import STRINGS as MP
from suite.moreinfo.strings import STRINGS as MI
from suite.slidepilot.strings import SAMPLE_OUTLINE
from suite.slidepilot.strings import STRINGS as SL

TABLES = {"common": COMMON, "datapilot": DP, "bipilot": BI, "docpilot": DOC, "slidepilot": SL, "fraudpilot": FR,
          "icepilot": ICE, "mailpilot": MP, "moreinfo": MI}


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


def _source(module):
    return Path(module.__file__).read_text(encoding="utf-8")


def test_mailpilot_dynamic_keys_exist():
    t = Translator(COMMON, MP)
    keys = list(mp_app.SCOPES) + list(mp_app.RULE_SCOPES) + list(mp_app.PERIODS)
    keys += [k for k, _ in mp_app.QUICK_FILTERS + mp_app.BUILTIN_SEARCHES + tuple(model.PICKER_COLORS)]
    keys += list(phrases.TEMPLATES) + [f"pc_{k}" for k in phrases.PHRASES] + [f"tone_{k}" for k in mp_assist.TONES]
    keys += [f"kind_{k}" for k in mp_english.KINDS + ("card", "iban")]
    keys += [f"risk_{k}" for k in ("high", "medium", "low")]
    keys += [f"lvl_{k}" for k in ("very_easy", "easy", "medium", "hard")]
    keys += [f"col_{c}" for c in widgets.MessageList.WIDTHS if c != "state"]
    keys += [f"icol_{c}" for c in ("kind", "text", "suggestion")] + [f"rcol_{c}" for c in ("on", "name", "query")]
    keys += [f"rc_{k}" for k in ("subject", "body", "body_or_subject", "sender_address", "has_attachment",
                                 "importance")]
    keys += re.findall(r'"(ph_\w+)"', _source(mp_detectors))
    keys += [f"q_err_{c}" for c in re.findall(r'QueryError\("(\w+)"', _source(mp_query))]
    for module in (backend_base, backend_demo, backend_outlook):
        keys += [f"mp_err_{c}" for c in re.findall(r'BackendError\("(\w+)"', _source(module))]
    keys += re.findall(r'"((?:col|sug)_\w+)"', _source(mp_analysis)) + re.findall(r'"(rule_\w+)"', _source(mp_rules))
    for key in keys:
        t(key)
    assert not t.missing, t.missing


def test_mailpilot_english_messages_cover_every_rule():
    used = set(re.findall(r'"(?:spelling|grammar|esl|punctuation|style|tone|clarity)",\s*"(\w+)"\s*[,)]',
                          _source(mp_english))) - set(mp_english.KINDS)
    assert len(used) > 30 and used <= set(mp_english.MESSAGES), used - set(mp_english.MESSAGES)
    for rule, entry in mp_english.MESSAGES.items():
        assert len(entry) == 3 and fields(entry[0]) == fields(entry[1]) == fields(entry[2]), rule


def test_mailpilot_help_and_phrases_in_three_languages():
    assert set(MP_HELP) == set(LANGS)
    for category, items in phrases.PHRASES.items():
        assert items and all(len(p) == 3 and all(p) for p in items), category
