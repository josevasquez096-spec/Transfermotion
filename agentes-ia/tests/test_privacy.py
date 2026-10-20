from suite.privacy import Anonymizer, luhn_ok


def test_mask_and_unmask_roundtrip():
    a = Anonymizer()
    a.add_known("María López", "CLIENTE")
    text = ("María López (maria@mail.com, +34 612 345 678) reporta 1,250.00 USD el 2024-03-15 con la tarjeta "
            "4111 1111 1111 1111, cuenta 0123456789 e IBAN ES91 2100 0418 4502 0005 1332.")
    masked = a.mask(text)
    for secret in ("María", "maria@mail.com", "612 345 678", "4111", "0123456789", "ES91"):
        assert secret not in masked
    for kept in ("1,250.00", "2024-03-15"):
        assert kept in masked
    assert a.unmask(masked) == text


def test_same_value_same_token_and_luhn():
    a = Anonymizer()
    masked = a.mask("a@b.com y a@b.com")
    assert masked.count("[EMAIL_1]") == 2
    assert luhn_ok("4111111111111111") and not luhn_ok("4111111111111112")
    assert a.mask("1234 5678 9012 3456") == "1234 5678 9012 3456"  # no pasa Luhn: no es una tarjeta
