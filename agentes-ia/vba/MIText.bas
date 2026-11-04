Attribute VB_Name = "MIText"
' MoreInfo Pilot - text helpers that do not need Word: file names and numbering, dates, the language of a letter
' and the address typed on one line. (Same rules as the Python version in suite/moreinfo.)
Option Explicit

' Parts returned by SplitAddress (an array of 6 strings).
Public Const ADDR_LINE1 As Integer = 0
Public Const ADDR_LINE2 As Integer = 1
Public Const ADDR_CITY As Integer = 2
Public Const ADDR_PROVINCE As Integer = 3          ' province code, e.g. ON
Public Const ADDR_PROVINCE_WRITTEN As Integer = 4  ' as it was written, e.g. Ontario
Public Const ADDR_POSTAL As Integer = 5

' ---------------------------------------------------------------- characters

Public Function IsDigitChar(ByVal c As String) As Boolean
    If Len(c) = 0 Then Exit Function
    IsDigitChar = AscW(c) >= 48 And AscW(c) <= 57
End Function

Public Function IsAsciiLetter(ByVal c As String) As Boolean
    Dim a As Long
    If Len(c) = 0 Then Exit Function
    a = AscW(c)
    IsAsciiLetter = (a >= 65 And a <= 90) Or (a >= 97 And a <= 122)
End Function

Public Function IsAsciiAlnum(ByVal c As String) As Boolean
    IsAsciiAlnum = IsAsciiLetter(c) Or IsDigitChar(c)
End Function

' Letter, digit or underscore (also accented letters): what a regular expression calls a "word" character.
Public Function IsWordChar(ByVal c As String) As Boolean
    If Len(c) = 0 Then Exit Function
    IsWordChar = IsAsciiAlnum(c) Or c = "_" Or AscW(c) > 127
End Function

' Lower case without accents ("Quebec" for "Qu" & ChrW(233) & "bec"), trimmed: to compare names.
Public Function Fold(ByVal s As String) As String
    Dim accents As Variant, plain As String, i As Long, j As Long, c As String, out As String
    accents = Array(225, 224, 226, 228, 227, 229, 233, 232, 234, 235, 237, 236, 238, 239, 243, 242, 244, 246, 245, _
                    250, 249, 251, 252, 231, 241, 253, 255)
    plain = "aaaaaaeeeeiiiiooooouuuucnyy"
    s = LCase$(Trim$(s))
    For i = 1 To Len(s)
        c = Mid$(s, i, 1)
        If AscW(c) > 127 Then
            For j = 0 To UBound(accents)
                If AscW(c) = accents(j) Then
                    c = Mid$(plain, j + 1, 1)
                    Exit For
                End If
            Next
        End If
        out = out & c
    Next
    Fold = out
End Function

' Removes the given characters from both ends ("Toronto." -> "Toronto" with " .;").
Public Function StripChars(ByVal s As String, ByVal chars As String) As String
    Do While Len(s) > 0
        If InStr(1, chars, Left$(s, 1)) = 0 Then Exit Do
        s = Mid$(s, 2)
    Loop
    Do While Len(s) > 0
        If InStr(1, chars, Right$(s, 1)) = 0 Then Exit Do
        s = Left$(s, Len(s) - 1)
    Loop
    StripChars = s
End Function

' Spaces, tabs and line breaks collapsed to one space, trimmed.
Public Function SingleSpaced(ByVal s As String) As String
    Dim i As Long, c As String, out As String, gap As Boolean
    For i = 1 To Len(s)
        c = Mid$(s, i, 1)
        If c = " " Or c = vbTab Or c = vbCr Or c = vbLf Or AscW(c) = 160 Then
            gap = True
        Else
            If gap And Len(out) > 0 Then out = out & " "
            gap = False
            out = out & c
        End If
    Next
    SingleSpaced = out
End Function

' ---------------------------------------------------------------- file names and numbering

' Case number safe for a file name (no \ / : * ? " < > | and no spaces).
Public Function CleanCase(ByVal s As String) As String
    Dim i As Long, c As String, out As String
    For i = 1 To Len(s)
        c = Mid$(s, i, 1)
        If InStr(1, "\/:*?""<>|", c) = 0 And c <> " " And c <> vbTab And c <> vbCr And c <> vbLf Then out = out & c
    Next
    CleanCase = out
End Function

' Lower-case extension with the dot (".pdf"), or "" when there is none.
Public Function FileExt(ByVal path As String) As String
    Dim dotPos As Long, slashPos As Long
    dotPos = InStrRev(path, ".")
    slashPos = InStrRev(path, "\")
    If dotPos > 0 And dotPos > slashPos Then FileExt = LCase$(Mid$(path, dotPos))
End Function

Public Function FileNameOf(ByVal path As String) As String
    FileNameOf = Mid$(path, InStrRev(path, "\") + 1)
End Function

Public Function IsWordType(ByVal ext As String) As Boolean
    IsWordType = InStr(1, "|.docx|.doc|.rtf|.odt|.docm|.dotx|", "|" & LCase$(ext) & "|") > 0
End Function

Public Function IsImageType(ByVal ext As String) As Boolean
    IsImageType = InStr(1, "|.png|.jpg|.jpeg|.bmp|.gif|.tif|.tiff|", "|" & LCase$(ext) & "|") > 0
End Function

' Extension a case document is saved with: Word files and images become PDF; Excel, text and emails keep theirs.
Public Function DocumentTarget(ByVal path As String) As String
    Dim ext As String
    ext = FileExt(path)
    If IsWordType(ext) Or IsImageType(ext) Or ext = ".pdf" Then
        DocumentTarget = ".pdf"
    Else
        DocumentTarget = ext
    End If
End Function

' Number used by an existing file of the case: CASE,MOREINFO.pdf -> 0, CASE,MOREINFO3.xlsx -> 3, other -> -1.
Public Function TakenNumber(ByVal fileName As String, ByVal caseNo As String, ByVal baseName As String) As Long
    Dim prefix As String, rest As String, digits As String, i As Long
    TakenNumber = -1
    prefix = LCase$(caseNo & "," & baseName)
    If Len(fileName) <= Len(prefix) Then Exit Function
    If LCase$(Left$(fileName, Len(prefix))) <> prefix Then Exit Function
    rest = Mid$(fileName, Len(prefix) + 1)
    i = 1
    Do While i <= Len(rest)
        If Not IsDigitChar(Mid$(rest, i, 1)) Then Exit Do
        i = i + 1
    Loop
    digits = Left$(rest, i - 1)
    rest = Mid$(rest, i)
    If Len(rest) < 2 Or Left$(rest, 1) <> "." Then Exit Function   ' the extension follows
    If InStr(2, rest, ".") > 0 Then Exit Function
    If Len(digits) > 9 Then Exit Function
    If Len(digits) = 0 Then TakenNumber = 0 Else TakenNumber = CLng(digits)
End Function

' Free names for several files, in order: CASE,BASE.ext, then CASE,BASE1.ext, CASE,BASE2.ext...
' usedList holds the numbers already taken as "|0||3|".
Public Function NextNames(ByVal caseNo As String, ByVal baseName As String, ByVal usedList As String, _
                          ByVal exts As Variant) As Variant
    Dim names() As String, i As Long, n As Long
    ReDim names(LBound(exts) To UBound(exts))
    For i = LBound(exts) To UBound(exts)
        Do While InStr(1, usedList, "|" & CStr(n) & "|") > 0
            n = n + 1
        Loop
        If n = 0 Then
            names(i) = caseNo & "," & baseName & LCase$(exts(i))
        Else
            names(i) = caseNo & "," & baseName & CStr(n) & LCase$(exts(i))
        End If
        usedList = usedList & "|" & CStr(n) & "|"
    Next
    NextNames = names
End Function

' ---------------------------------------------------------------- dates and language

Public Function MonthName2(ByVal lang As String, ByVal m As Integer) As String
    Dim names As Variant
    Select Case lang
        Case "fr"
            names = Array("janvier", "f" & ChrW(233) & "vrier", "mars", "avril", "mai", "juin", "juillet", _
                          "ao" & ChrW(251) & "t", "septembre", "octobre", "novembre", "d" & ChrW(233) & "cembre")
        Case "es"
            names = Array("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", _
                          "octubre", "noviembre", "diciembre")
        Case Else
            names = Array("January", "February", "March", "April", "May", "June", "July", "August", "September", _
                          "October", "November", "December")
    End Select
    MonthName2 = names(m - 1)
End Function

' "November 4, 2026" (en) or "4 novembre 2026" (fr, es).
Public Function DateText(ByVal lang As String, ByVal d As Date) As String
    If lang = "fr" Or lang = "es" Then
        DateText = Day(d) & " " & MonthName2(lang, Month(d)) & " " & Year(d)
    Else
        DateText = MonthName2("en", Month(d)) & " " & Day(d) & ", " & Year(d)
    End If
End Function

' Language of a letter (en, fr or es), from its most common small words.
Public Function GuessLanguage(ByVal text As String) As String
    Dim words As Variant, w As Variant, scores(2) As Long, lists As Variant, k As Integer, best As Integer
    Dim langs As Variant
    lists = Array("|the|you|your|we|dear|and|is|for|of|to|", _
                  "|le|la|les|des|vous|votre|nous|madame|monsieur|et|est|pour|", _
                  "|el|los|las|usted|su|nosotros|senor|senora|y|para|del|")
    words = Split(LettersOnly(Fold(text)), " ")
    For Each w In words
        If Len(w) > 0 Then
            For k = 0 To 2
                If InStr(1, lists(k), "|" & w & "|") > 0 Then scores(k) = scores(k) + 1
            Next
        End If
    Next
    best = 0
    For k = 1 To 2
        If scores(k) > scores(best) Then best = k
    Next
    langs = Array("en", "fr", "es")
    GuessLanguage = langs(best)
End Function

Private Function LettersOnly(ByVal s As String) As String
    Dim i As Long, c As String, out As String
    For i = 1 To Len(s)
        c = Mid$(s, i, 1)
        If IsAsciiLetter(c) Then out = out & c Else out = out & " "
    Next
    LettersOnly = out
End Function

' ---------------------------------------------------------------- address typed on one line

' Province codes and names (folded: lower case, no accents), as pairs.
Private Function Provinces() As Variant
    Provinces = Array("AB", "ab", "AB", "alberta", "BC", "bc", "BC", "british columbia", "BC", "colombie-britannique", _
        "MB", "mb", "MB", "manitoba", "NB", "nb", "NB", "new brunswick", "NB", "nouveau-brunswick", _
        "NL", "nl", "NL", "newfoundland and labrador", "NL", "terre-neuve-et-labrador", "NL", "newfoundland", _
        "NS", "ns", "NS", "nova scotia", "NS", "nouvelle-ecosse", "NT", "nt", "NT", "northwest territories", _
        "NT", "territoires du nord-ouest", "NU", "nu", "NU", "nunavut", "ON", "on", "ON", "ontario", _
        "PE", "pe", "PE", "prince edward island", "PE", "ile-du-prince-edouard", "PE", "pei", _
        "QC", "qc", "QC", "quebec", "QC", "pq", "SK", "sk", "SK", "saskatchewan", "YT", "yt", "YT", "yukon")
End Function

' Every name of a province (code and names, folded), for matching a drop-down option.
Public Function ProvinceKeys(ByVal code As String) As String
    Dim p As Variant, i As Long, out As String
    p = Provinces()
    For i = 0 To UBound(p) Step 2
        If p(i) = code Then out = out & "|" & p(i + 1)
    Next
    ProvinceKeys = out & "|"
End Function

' True when the text ends with a province (code or name). Returns the code, the name as written and the rest.
Public Function ProvinceMatch(ByVal part As String, ByRef code As String, ByRef written As String, _
                              ByRef rest As String) As Boolean
    Dim p As Variant, i As Long, key As String, folded As String, bestLen As Long, best As Long
    part = Trim$(part)
    folded = Fold(part)
    p = Provinces()
    best = -1
    For i = 0 To UBound(p) Step 2
        key = p(i + 1)
        If folded = key Or Right$(folded, Len(key) + 1) = " " & key Then
            If Len(key) > bestLen Then
                bestLen = Len(key)
                best = i
            End If
        End If
    Next
    If best < 0 Then Exit Function
    code = p(best)
    written = Trim$(Right$(part, bestLen))
    rest = Trim$(Left$(part, Len(part) - bestLen))
    ProvinceMatch = True
End Function

' The province as the template's drop-down lists it (code or name), or as it was written.
Public Function ProvinceOption(ByVal code As String, ByVal written As String, ByVal options As Variant) As String
    Dim keys As String, o As Variant, hasOptions As Boolean
    If IsArray(options) Then hasOptions = UBound(options) >= LBound(options)
    If Not hasOptions Then
        If Len(written) > 2 Then ProvinceOption = written Else ProvinceOption = code
        Exit Function
    End If
    keys = ProvinceKeys(code)
    For Each o In options
        If InStr(1, keys, "|" & Fold(CStr(o)) & "|") > 0 Then
            ProvinceOption = CStr(o)
            Exit Function
        End If
    Next
End Function

' True for a Canadian postal code written as A1A 1A1.
Public Function ValidPostal(ByVal v As String) As Boolean
    If Len(v) <> 7 Then Exit Function
    If Mid$(v, 4, 1) <> " " Then Exit Function
    ValidPostal = IsUpperLetter(Mid$(v, 1, 1)) And IsDigitChar(Mid$(v, 2, 1)) And IsUpperLetter(Mid$(v, 3, 1)) _
        And IsDigitChar(Mid$(v, 5, 1)) And IsUpperLetter(Mid$(v, 6, 1)) And IsDigitChar(Mid$(v, 7, 1))
End Function

Private Function IsUpperLetter(ByVal c As String) As Boolean
    If Len(c) = 0 Then Exit Function
    IsUpperLetter = AscW(c) >= 65 And AscW(c) <= 90
End Function

' A1A 1A1 / A1A1A1 / A1A-1A1 starting at position i (word boundaries around). Returns the end position or 0.
Private Function PostalAt(ByVal s As String, ByVal i As Long) As Long
    Dim j As Long, attempt As Integer
    If i > 1 Then
        If IsWordChar(Mid$(s, i - 1, 1)) Then Exit Function
    End If
    If Not (IsAsciiLetter(Mid$(s, i, 1)) And IsDigitChar(Mid$(s, i + 1, 1)) And IsAsciiLetter(Mid$(s, i + 2, 1))) Then _
        Exit Function
    For attempt = 1 To 2   ' with a space or dash first, then without
        If attempt = 1 Then
            j = i + 4
            If Mid$(s, i + 3, 1) <> " " And Mid$(s, i + 3, 1) <> "-" Then GoTo NextTry
        Else
            j = i + 3
        End If
        If IsDigitChar(Mid$(s, j, 1)) And IsAsciiLetter(Mid$(s, j + 1, 1)) And IsDigitChar(Mid$(s, j + 2, 1)) Then
            If j + 2 = Len(s) Then
                PostalAt = j + 2
                Exit Function
            ElseIf Not IsWordChar(Mid$(s, j + 3, 1)) Then
                PostalAt = j + 2
                Exit Function
            End If
        End If
NextTry:
    Next
End Function

' The address split into its parts (see ADDR_*). Accepts "221 Main Street, Apt 4B, Toronto ON M5V 2T6",
' "123 rue Principale, app. 4, Montreal (Quebec) H2X 1Y4", with or without commas.
Public Function SplitAddress(ByVal text As String) As Variant
    Dim out(5) As String, s As String, i As Long, e As Long, mStart As Long, mEnd As Long
    Dim t As String, parts As Variant, kept() As String, n As Long, k As Long
    Dim code As String, written As String, rest As String, line1 As String, unitText As String, unitPos As Long
    Dim street As Variant

    s = Replace(Replace(Replace(text, vbCrLf, ", "), vbCr, ", "), vbLf, ", ")
    s = SingleSpaced(Replace(Replace(s, "(", ","), ")", ","))

    ' postal code: the last A1A 1A1; or one with a typo at the end; or a US ZIP code
    i = 1
    Do While i <= Len(s) - 5
        e = PostalAt(s, i)
        If e > 0 Then
            mStart = i
            mEnd = e
            i = e + 1
        Else
            i = i + 1
        End If
    Loop
    If mStart > 0 Then
        t = Mid$(s, mStart, mEnd - mStart + 1)
        out(ADDR_POSTAL) = UCase$(Left$(t, 3) & " " & Right$(t, 3))
        s = Left$(s, mStart - 1) & "," & Mid$(s, mEnd + 1)
    ElseIf LoosePostal(s, t, mStart) Then
        out(ADDR_POSTAL) = t
        s = Left$(s, mStart - 1) & ","
    ElseIf ZipCode(s, t, mStart) Then
        out(ADDR_POSTAL) = t
        s = Left$(s, mStart - 1)
    End If

    parts = Split(s, ",")
    ReDim kept(0 To UBound(parts) + 3)
    n = 0
    For k = 0 To UBound(parts)
        t = StripChars(Trim$(parts(k)), " .;")
        If Len(t) > 0 Then
            kept(n) = t
            n = n + 1
        End If
    Next
    If n > 0 Then
        If Fold(kept(n - 1)) = "canada" Then n = n - 1
    End If
    If n > 0 Then
        If ProvinceMatch(kept(n - 1), code, written, rest) Then
            If Len(rest) > 0 Or n > 1 Then
                out(ADDR_PROVINCE) = code
                out(ADDR_PROVINCE_WRITTEN) = written
                If Len(rest) > 0 Then kept(n - 1) = rest Else n = n - 1
            End If
        End If
    End If

    If n = 1 Then
        street = SplitStreet(kept(0))   ' no commas: the street type tells where the street ends
        n = 0
        For k = 0 To 2
            If Len(street(k)) > 0 Then
                kept(n) = street(k)
                n = n + 1
            End If
        Next
        If n = 1 Then
            out(ADDR_LINE1) = kept(0)
            SplitAddress = out
            Exit Function
        End If
        out(ADDR_CITY) = kept(n - 1)
        n = n - 1
    ElseIf n > 1 Then
        out(ADDR_CITY) = kept(n - 1)
        n = n - 1
    End If
    If n > 0 Then
        line1 = kept(0)
        If n = 1 Then
            If UnitAtEnd(line1, unitPos, unitText) Then   ' "221 Main Street Apt 4B, Toronto"
                If unitPos > 1 Then
                    out(ADDR_LINE2) = unitText
                    line1 = Trim$(Left$(line1, unitPos - 1))
                End If
            End If
        Else
            For k = 1 To n - 1
                If Len(out(ADDR_LINE2)) > 0 Then out(ADDR_LINE2) = out(ADDR_LINE2) & ", "
                out(ADDR_LINE2) = out(ADDR_LINE2) & kept(k)
            Next
        End If
        out(ADDR_LINE1) = line1
    End If
    SplitAddress = out
End Function

' Two groups of 3 letters/digits at the end that look like a postal code typed with a mistake ("M5V 2ST").
Private Function LoosePostal(ByVal s As String, ByRef code As String, ByRef startPos As Long) As Boolean
    Dim t As String, cand As String, g As Long, k As Long, letters As Long, digits As Long, b As Long
    Dim c1 As String, w As String, r As String
    t = s
    Do While Len(t) > 0
        If InStr(1, " ,.", Right$(t, 1)) = 0 Then Exit Do
        t = Left$(t, Len(t) - 1)
    Loop
    For g = 7 To 6 Step -1   ' "A1A 1A1" first, then "A1A1A1"
        If Len(t) >= g Then
            cand = Right$(t, g)
            If g = 7 Then
                If Mid$(cand, 4, 1) <> " " And Mid$(cand, 4, 1) <> "-" Then GoTo NextSize
                cand = Left$(cand, 3) & Right$(cand, 3)
            End If
            For k = 1 To 6
                If Not IsAsciiAlnum(Mid$(cand, k, 1)) Then GoTo NextSize
            Next
            If Not IsAsciiLetter(Left$(cand, 1)) Then GoTo NextSize
            b = Len(t) - g   ' character before the code: start, space or comma
            If b > 0 Then
                If Mid$(t, b, 1) <> " " And Mid$(t, b, 1) <> "," Then GoTo NextSize
            End If
            letters = 0
            digits = 0
            For k = 1 To 6
                If IsDigitChar(Mid$(cand, k, 1)) Then digits = digits + 1 Else letters = letters + 1
            Next
            If digits < 2 Or letters < 2 Then GoTo NextSize   ' plain words ("Bay Way") are not postal codes
            If ProvinceMatch(Right$(t, g), c1, w, r) Then GoTo NextSize
            code = UCase$(Left$(cand, 3) & " " & Right$(cand, 3))
            If b > 0 Then startPos = b Else startPos = 1
            LoosePostal = True
            Exit Function
        End If
NextSize:
    Next
End Function

' A US ZIP code (12345 or 12345-6789) at the end.
Private Function ZipCode(ByVal s As String, ByRef code As String, ByRef startPos As Long) As Boolean
    Dim t As String, k As Long, cand As String, ok As Boolean
    t = RTrim$(s)
    If Len(t) >= 10 Then
        cand = Right$(t, 10)
        ok = Mid$(cand, 6, 1) = "-"
        For k = 1 To 10
            If k <> 6 And Not IsDigitChar(Mid$(cand, k, 1)) Then ok = False
        Next
        If ok And Len(t) > 10 Then ok = Not IsWordChar(Mid$(t, Len(t) - 10, 1))
        If ok Then
            code = cand
            startPos = Len(t) - 9
            ZipCode = True
            Exit Function
        End If
    End If
    If Len(t) >= 5 Then
        cand = Right$(t, 5)
        ok = True
        For k = 1 To 5
            If Not IsDigitChar(Mid$(cand, k, 1)) Then ok = False
        Next
        If ok And Len(t) > 5 Then ok = Not IsWordChar(Mid$(t, Len(t) - 5, 1))
        If ok Then
            code = cand
            startPos = Len(t) - 4
            ZipCode = True
        End If
    End If
End Function

Private Function IsUnitMarker(ByVal word As String) As Boolean
    IsUnitMarker = InStr(1, "|apt|apt.|apartment|suite|ste|ste.|unit|app|app.|appartement|bureau|room|#|", _
                         "|" & Fold(word) & "|") > 0
End Function

' A unit at the end of the text ("Apt 4B", "Suite 1801", "#12"). Returns where it starts and its text.
Public Function UnitAtEnd(ByVal text As String, ByRef unitPos As Long, ByRef unitText As String) As Boolean
    Dim words As Variant, n As Long, last As String, before As String, m As Variant, f As String
    text = Trim$(text)
    If Len(text) = 0 Then Exit Function
    words = Split(text, " ")
    n = UBound(words)
    If n >= 1 Then
        If IsUnitMarker(words(n - 1)) Then
            unitText = words(n - 1) & " " & words(n)
            unitPos = Len(text) - Len(unitText) + 1
            UnitAtEnd = True
            Exit Function
        End If
    End If
    last = words(n)
    f = Fold(last)
    For Each m In Array("#", "apartment", "appartement", "apt.", "apt", "app.", "app", "suite", "ste.", "ste", _
                        "unit", "bureau", "room")
        If Len(f) > Len(m) And Left$(f, Len(m)) = m Then
            If HasDigit(Mid$(last, Len(m) + 1)) Then   ' "Apt4B", "#12" (not plain words such as "Appleby")
                unitText = last
                unitPos = Len(text) - Len(last) + 1
                UnitAtEnd = True
                Exit Function
            End If
        End If
    Next
End Function

Private Function HasDigit(ByVal s As String) As Boolean
    Dim i As Long
    For i = 1 To Len(s)
        If IsDigitChar(Mid$(s, i, 1)) Then
            HasDigit = True
            Exit Function
        End If
    Next
End Function

Private Function IsStreetType(ByVal word As String) As Boolean
    IsStreetType = InStr(1, "|st|street|ave|avenue|rd|road|blvd|boulevard|dr|drive|way|lane|ln|cres|crescent|crt|" & _
        "court|ct|pl|place|terr|terrace|trail|trl|pkwy|parkway|hwy|highway|cir|circle|sq|square|gate|grove|row|" & _
        "line|sideroad|concession|close|path|heights|hts|gardens|gdns|park|walk|cove|mews|", _
        "|" & StripChars(Fold(word), ".") & "|") > 0
End Function

Private Function IsDirection(ByVal word As String) As Boolean
    IsDirection = InStr(1, "|n|s|e|w|ne|nw|se|sw|north|south|east|west|nord|sud|est|ouest|o|", _
                        "|" & StripChars(Fold(word), ".") & "|") > 0
End Function

' "221 Main Street Apt 4B Toronto" (no commas) -> street, unit, city; the street type marks the end of the street.
Public Function SplitStreet(ByVal text As String) As Variant
    Dim words As Variant, i As Long, k As Long, endPos As Long, n As Long, head As String, unit As String
    Dim restStart As Long, city As String
    words = Split(text, " ")
    n = UBound(words) + 1
    For i = n - 1 To 1 Step -1
        If IsStreetType(words(i)) Then
            head = ""
            For k = 0 To i - 1
                head = head & words(k) & " "
            Next
            If HasDigit(head) Then
                endPos = i + 1
                If endPos < n Then
                    If IsDirection(words(endPos)) Then endPos = endPos + 1
                End If
                head = ""
                For k = 0 To endPos - 1
                    If k > 0 Then head = head & " "
                    head = head & words(k)
                Next
                restStart = endPos
                If restStart < n Then
                    If Left$(words(restStart), 1) = "#" And Len(words(restStart)) > 1 Then   ' "#12"
                        unit = words(restStart)
                        restStart = restStart + 1
                    ElseIf restStart + 1 < n Then
                        If IsUnitMarker(words(restStart)) Then   ' "Apt 4B", "Suite 1801"
                            unit = words(restStart) & " " & words(restStart + 1)
                            restStart = restStart + 2
                        End If
                    End If
                End If
                For k = restStart To n - 1
                    If Len(city) > 0 Then city = city & " "
                    city = city & words(k)
                Next
                SplitStreet = Array(head, unit, city)
                Exit Function
            End If
        End If
    Next
    SplitStreet = Array(text, "", "")
End Function

' Role of an address field from its label: line1, line2, city, province, postal or "". Roles already given to
' another field ("|line1|city|") are skipped.
Public Function AddressRole(ByVal label As String, Optional ByVal assigned As String = "") As String
    Dim f As String, roles As Variant, words As Variant, r As Long, w As Variant
    f = Fold(label)
    roles = Array("line2", "postal", "province", "city", "line1")
    words = Array(Array("line 2", "address 2", "ligne 2", "adresse 2", "suite", "apt", "unit", "appartement"), _
                  Array("postal", "zip", "code postal"), _
                  Array("province", "state", "prov"), _
                  Array("city", "ville", "town", "municipalit"), _
                  Array("line 1", "address 1", "ligne 1", "adresse 1", "street", "rue", "address", "adresse"))
    For r = 0 To 4
        If InStr(1, assigned, "|" & roles(r) & "|") > 0 Then GoTo NextRole
        For Each w In words(r)
            If InStr(1, f, w) > 0 Then
                AddressRole = roles(r)
                Exit Function
            End If
        Next
NextRole:
    Next
End Function

' ---------------------------------------------------------------- placeholders written in the letter

' Labels of the placeholders written as [Customer Name] or {{Customer Name}}, in order, without repeats
' (an array; empty when there are none).
Public Function PlaceholderLabels(ByVal text As String) As Variant
    Dim i As Long, j As Long, inner As String, label As String, found As String, sep As String
    sep = Chr(30)
    i = 1
    Do While i <= Len(text)
        label = ""
        If Mid$(text, i, 2) = "{{" Then
            j = InStr(i + 2, text, "}}")
            If j > 0 Then
                inner = Mid$(text, i + 2, j - i - 2)
                If Len(Trim$(inner)) >= 1 And Len(Trim$(inner)) <= 60 And NoBreaks(inner, "{}") Then
                    label = Trim$(inner)
                    i = j + 1
                End If
            End If
        ElseIf Mid$(text, i, 1) = "[" Then
            j = InStr(i + 1, text, "]")
            If j > 0 Then
                inner = Mid$(text, i + 1, j - i - 1)
                If Len(inner) >= 2 And Len(inner) <= 60 And NoBreaks(inner, "[]") Then
                    label = Trim$(inner)
                    i = j
                End If
            End If
        End If
        If Len(label) > 0 Then
            If InStr(1, sep & LCase$(found) & sep, sep & LCase$(label) & sep) = 0 Then
                If Len(found) > 0 Then found = found & sep
                found = found & label
            End If
        End If
        i = i + 1
    Loop
    If Len(found) = 0 Then
        PlaceholderLabels = Array()
    Else
        PlaceholderLabels = Split(found, sep)
    End If
End Function

Private Function NoBreaks(ByVal s As String, ByVal brackets As String) As Boolean
    Dim k As Long, c As String
    For k = 1 To Len(s)
        c = Mid$(s, k, 1)
        If InStr(1, brackets, c) > 0 Or c = vbCr Or c = vbLf Or c = Chr(7) Or c = Chr(11) Then Exit Function
    Next
    NoBreaks = True
End Function
