Attribute VB_Name = "mInterp"
Option Explicit

Function CSplineA(Xa As Variant, YA As Variant, Xint As Variant, Optional Out As Long = 1, Optional etype As Long = 1, Optional End1 As Double = 0, Optional End2 As Double = 0)


' ETypes: 1 = Specified 2nd derivative, 2 = Specified slope
' End1 and End2 = specified curvature or slope

    Dim i As Long, n As Long, Yint As Variant

    Dim y2() As Double
    Dim A() As Double, B() As Double, C() As Double, R() As Double
    Dim x_1 As Double, y_1 As Double, y_2 As Double, Area As Double

    If TypeName(Xa) = "Range" Then Xa = Xa.Value2
    If TypeName(YA) = "Range" Then YA = YA.Value2

    n = UBound(Xa)

    If IsArray(Xint) = False Then
        If Xint > Xa(n, 1) Then
            ReDim Yint(1 To 1, 1 To 1)
            Yint(1, 1) = YA(n, 1)
            CSplineA = Yint
            Exit Function
        End If
    End If


    ReDim l(1 To n - 1)
    ReDim m(1 To n - 1)


    For i = 1 To n - 1
        l(i) = Xa(i + 1, 1) - Xa(i, 1)
        m(i) = (YA(i + 1, 1) - YA(i, 1)) / l(i)
    Next i


    ReDim A(1 To n, 1 To 1)
    ReDim B(1 To n, 1 To 1)
    ReDim C(1 To n, 1 To 1)
    ReDim R(1 To n, 1 To 1)

    ' Form arrays a, b, c, and r for Tridiag
    Select Case etype
    Case 1

        R(1, 1) = End1
        R(n, 1) = End2

        A(1, 1) = 0
        B(1, 1) = 1
        C(1, 1) = 0

        A(n, 1) = 0
        B(n, 1) = 1
        C(n, 1) = 0


    Case 2
        R(1, 1) = 6 * (m(1) - End1)
        R(n, 1) = 6 * (End2 - m(n - 1))
        B(1, 1) = 2 * l(1)
        C(1, 1) = l(1)
        A(1, 1) = 0

        C(n, 1) = 0
        A(n, 1) = l(n - 1)
        B(n, 1) = 2 * l(n - 1)

    End Select

    For i = 2 To n - 1
        A(i, 1) = l(i - 1)
        B(i, 1) = 2 * (l(i - 1) + l(i))
        C(i, 1) = l(i)
        R(i, 1) = 6 * (m(i) - m(i - 1))
    Next i

    y2 = TriSolve(A, B, C, R)

    For i = 1 To n - 1
        y2(i, 2) = YA(i, 1)
        y2(i, 3) = m(i) - (l(i) / 6) * (2 * y2(i, 1) + y2(i + 1, 1))
        y2(i, 4) = y2(i, 1) / 2
        y2(i, 5) = (y2(i + 1, 1) - y2(i, 1)) / (6 * l(i))
    Next i

    If Out = 2 Then
        CSplineA = y2

    ElseIf Out = 1 Then

        Yint = Splineint(Xa, YA, y2, Xint)
        CSplineA = Yint
    Else: CSplineA = "Invalid ""Out"" value"
    End If
End Function

Function Splineint(Xa As Variant, YA As Variant, y2a As Variant, Xint As Variant) As Variant

    Dim i As Long, j As Long, n As Long, nInt As Long
    Dim X As Double, xd1 As Double, xd2 As Double, B As Double, A As Double, Y() As Double
    Dim x_1 As Double, x_2 As Double, xi As Double
    Dim l As Double, m As Double, C As Double, D As Double
    Dim Chord As Double, ArcAng As Double, AvR As Double

    If TypeName(Xint) = "Range" Then Xint = Xint.Value2


    n = UBound(Xa)
    If IsArray(Xint) = True Then
        nInt = UBound(Xint)
    Else
        nInt = 1
        X = Xint
    End If

    ReDim Y(1 To nInt, 1 To 6)


    j = 1
    For i = 1 To nInt
        ' Find segment
        If nInt > 1 Then X = Xint(i, 1)

        xd1 = -1
        xd2 = -1
        If X > Xa(j, 1) Then
            Do While ((xd1 < 0 And xd2 < 0) Or (xd1 > 0 And xd2 > 0)) And (j < n)
                x_1 = Xa(j, 1)
                x_2 = Xa(j + 1, 1)
                xd1 = x_1 - X
                xd2 = x_2 - X
                j = j + 1
            Loop
            j = j - 1
        Else
            j = 1
        End If

        xi = X - Xa(j, 1)
        l = Xa(j + 1, 1) - Xa(j, 1)
        m = (YA(j + 1, 1) - YA(j, 1)) / l
        A = y2a(j, 2)
        B = y2a(j, 3)
        C = y2a(j, 4)
        D = y2a(j, 5)

        Y(i, 1) = A + B * xi + C * xi ^ 2 + D * xi ^ 3
        Y(i, 2) = B + 2 * C * xi + 3 * D * xi ^ 2
        Y(i, 3) = 2 * C + 6 * D * xi

        If Abs(Y(i, 3)) > 0.0000000001 Then
            Y(i, 4) = (1 + Y(i, 2) ^ 2) ^ (3 / 2) / Y(i, 3)
        End If
        If i > 1 Then
            Chord = ((Xint(i, 1) - Xint(i - 1, 1)) ^ 2 + (Y(i, 1) - Y(i - 1, 1)) ^ 2) ^ 0.5
            ArcAng = Atn(Y(i, 2)) - Atn(Y(i - 1, 2))
            If ArcAng <> 0 Then AvR = Chord / 2 / Sin(ArcAng / 2)
            Y(i, 5) = ArcAng * AvR
            Y(i, 6) = Chord
        Else
        End If

    Next i
    Splineint = Y
End Function


Function TriSolve(A As Variant, B As Variant, C As Variant, R As Variant) As Variant
    Dim U() As Double, n As Long

    Dim j As Long, bet As Double, gam() As Double
    If TypeName(A) = "Range" Then A = A.Value2
    If TypeName(B) = "Range" Then B = B.Value2
    If TypeName(C) = "Range" Then C = C.Value2
    If TypeName(R) = "Range" Then R = R.Value2

    n = UBound(A)
    ReDim U(1 To n, 1 To 5)
    ReDim gam(1 To n)

    If (B(1, 1) <> 0#) Then

        bet = B(1, 1)
        U(1, 1) = R(1, 1) / bet
    End If
    For j = 2 To n
        gam(j) = C(j - 1, 1) / bet
        bet = B(j, 1) - A(j, 1) * gam(j)
        If (bet <> 0#) Then
            U(j, 1) = (R(j, 1) - A(j, 1) * U(j - 1, 1)) / bet
        End If
    Next j
    For j = (n - 1) To 1 Step -1
        U(j, 1) = U(j, 1) - gam(j + 1) * U(j + 1, 1)

    Next j
    TriSolve = U
End Function

Function CardSpline(Xa As Variant, YA As Variant, Pint As Variant, Tens As Double, Optional PType As String = "L") As Variant
    Dim s As Double, U As Double, UA(1 To 1, 1 To 4) As Double, CardA(1 To 4, 1 To 4) As Double, Card2A As Variant
    Dim XA2() As Double, YA2() As Double, XYA As Variant, n As Long, nInt As Long, i As Long, j As Long, k As Long
    Dim XA3(1 To 4, 1 To 1) As Double, YA3(1 To 4, 1 To 1) As Double

    If TypeName(Xa) = "Range" Then Xa = Xa.Value2
    If TypeName(YA) = "Range" Then YA = YA.Value2
    If TypeName(Pint) = "Range" Then Pint = Pint.Value2

    n = UBound(Xa)
    nInt = UBound(Pint)
    ReDim XA2(1 To 4, 1 To n)
    ReDim YA2(1 To 4, 1 To n)

    s = (1 - Tens) / 2

    CardA(1, 1) = (-s)
    CardA(1, 2) = (2 - s)
    CardA(1, 3) = (s - 2)
    CardA(1, 4) = (s)
    CardA(2, 1) = (2 * s)
    CardA(2, 2) = (s - 3)
    CardA(2, 3) = (3 - (2 * s))
    CardA(2, 4) = (-1 * s)
    CardA(3, 1) = (-1 * s)
    CardA(3, 2) = (0)
    CardA(3, 3) = (s)
    CardA(3, 4) = (0)
    CardA(4, 1) = (0)
    CardA(4, 2) = (1)
    CardA(4, 3) = (0)
    CardA(4, 4) = (0)


    For i = 2 To n - 2
        XA2(1, i) = Xa(i - 1, 1)
        XA2(2, i) = Xa(i, 1)
        XA2(3, i) = Xa(i + 1, 1)
        XA2(4, i) = Xa(i + 2, 1)

        YA2(1, i) = YA(i - 1, 1)
        YA2(2, i) = YA(i, 1)
        YA2(3, i) = YA(i + 1, 1)
        YA2(4, i) = YA(i + 2, 1)
    Next i

    PType = UCase(PType)

    If PType = "L" Then
        ReDim XYA(1 To nInt, 1 To 2)
        For j = 1 To nInt


            i = Pint(j, 1)
            If Abs(Pint(j, 1) - i) > 0.00000000000001 Then
                i = Int(Pint(j, 1))
                U = Pint(j, 1) - i
            Else
                If i > 1 Then
                    i = Pint(j, 1) - 1
                    U = 1
                Else
                    i = 1
                    U = 0
                End If
            End If
            i = i + 1
            UA(1, 1) = U ^ 3
            UA(1, 2) = U ^ 2
            UA(1, 3) = U
            UA(1, 4) = 1

            For k = 1 To 4
                XA3(k, 1) = XA2(k, i)
                YA3(k, 1) = YA2(k, i)
            Next k

            Card2A = MMult(UA, CardA)
            XYA(j, 1) = MMult(Card2A, XA3)
            XYA(j, 2) = MMult(Card2A, YA3)
        Next j

    ElseIf PType = "X" Or PType = "Y" Then
       ' XYA = SolveCardSpline(Pint, XA2, YA2, CardA, n, PType)
    Else
        XYA(1, 1) = "Invalid PType"
    End If

    CardSpline = XYA    'CardA
End Function

Function CHSplineA(Xa As Variant, YA As Variant, Xint As Variant, Optional Mono As Boolean = False, Optional Out As Double = 1)


' ETypes: 1 = Specified 2nd derivative, 2 = Specified slope
' End1 and End2 = specified curvature or slope

    Dim i As Long, n As Long, nInt As Long, Yint() As Double, j As Long, t As Double
    Dim l() As Double, s() As Double, m() As Double, H() As Double, Cubica() As Double
    Dim Alpha As Double, Beta As Double, Tau As Double

    If TypeName(Xa) = "Range" Then Xa = Xa.Value2
    If TypeName(YA) = "Range" Then YA = YA.Value2
    If TypeName(Xint) = "Range" Then Xint = Xint.Value2

    n = UBound(Xa)
    nInt = UBound(Xint)

    ReDim l(1 To n - 1)
    ReDim s(1 To n)
    ReDim m(1 To n)
    ReDim H(1 To n)
    If Out = 1 Then
        ReDim Yint(1 To nInt, 1 To 1)
    Else
        ReDim Yint(1 To nInt, 1 To 2)
    End If
    ReDim Cubica(1 To n - 1, 1 To 4)

    i = 1
    l(i) = Xa(i + 1, 1) - Xa(i, 1)
    H(i) = YA(i + 1, 1) - YA(i, 1)
    s(i) = (H(i) / l(i))
    m(i) = s(i)
    For i = 2 To n - 1
        l(i) = Xa(i + 1, 1) - Xa(i, 1)
        H(i) = YA(i + 1, 1) - YA(i, 1)
        s(i) = (H(i) / l(i))
        m(i) = (s(i - 1) + s(i)) / 2
    Next i
    H(i) = H(i - 1)
    s(i) = s(i - 1)
    m(i) = s(i)

    If Mono = True Then
        For i = 1 To n - 1
            If m(i) <> 0 Then
                If H(i) = 0 Then
                    m(i) = 0
                    m(i + 1) = 0
                Else
                    Alpha = m(i) / H(i)
                    Beta = m(i + 1) / H(i)
                    If (Alpha = 0) Or (Beta = 0) Then
                        m(i) = 0
                        m(i + 1) = 0
                    ElseIf Alpha ^ 2 + Beta ^ 2 > 9 Then
                        Tau = 3 / (Alpha ^ 2 + Beta ^ 2) ^ 0.5
                        m(i) = Tau * Alpha * H(i)
                        m(i + 1) = Tau * Beta * H(i)
                    End If
                End If
            End If
        Next i
    End If

    For i = 1 To n - 1
        Cubica(i, 1) = 2 * (YA(i, 1) - YA(i + 1, 1)) + (m(i) + m(i + 1)) * l(i)
        Cubica(i, 2) = 3 * (YA(i + 1, 1) - YA(i, 1)) - (2 * m(i) + m(i + 1)) * l(i)
        Cubica(i, 3) = m(i) * l(i)
        Cubica(i, 4) = YA(i, 1)
    Next i

    For i = 1 To nInt
        j = 0
        Do
            j = j + 1
        Loop While (Xint(i, 1) > Xa(j + 1, 1) And j < n - 1)
        t = (Xint(i, 1) - Xa(j, 1)) / l(j)
        If Out = 1 Then
            Yint(i, 1) = Cubica(j, 1) * t ^ 3 + Cubica(j, 2) * t ^ 2 + Cubica(j, 3) * t + Cubica(j, 4)
        Else
            Yint(i, 1) = 3 * Cubica(j, 1) * t ^ 2 + 2 * Cubica(j, 2) * t + Cubica(j, 3)
            Yint(i, 2) = 6 * Cubica(j, 1) * t + 2 * Cubica(j, 2)
        End If
    Next i

    CHSplineA = Yint
End Function
Function TextString(TextRange As Variant, Optional Separate As String = " ") As String
    Dim Texta() As Variant, NumCells As Long, i As Long

    NumCells = TextRange.Columns.Count
    ReDim Texta(1 To 2, 1 To NumCells)
    For i = 1 To NumCells
        Texta(1, i) = TextRange(1, i).Value
        Texta(2, i) = TextRange(1, i).NumberFormat
    Next i


    If Texta(1, 1) <> "" Then
        TextString = Format(Texta(1, 1), Texta(2, 1))
    End If

    For i = 2 To NumCells
        If Texta(1, i) <> "" Then
            TextString = TextString & Separate & Format(Texta(1, i), Texta(2, i))
        End If
    Next i

End Function

Function TextStringA(DataA As Variant, FormatA As Variant, Optional Separate As String = " ") As Variant
    Dim Texta() As Variant, NumCells As Long, NumRows As Long, i As Long, TextA2() As Variant, j As Long, k As Long

    NumCells = UBound(DataA, 2)
    NumRows = UBound(DataA)
    ' ReDim TextA(1 To 2 * NumRows, 1 To NumCells)
    ReDim TextA2(1 To NumRows, 1 To 1)

    'For i = 1 To NumRows
    'k = (i - 1) * 2 + 1
    'For j = 1 To NumCells
    '    TextA(k, j) = TextRange(i, j).Value
    '    TextA(k + 1, j) = TextRange(i, j).NumberFormat
    'Next j
    'Next i

    For i = 1 To NumRows
        'k = (i - 1) * 2 + 1
        If DataA(i, 1) <> "" Then
            TextA2(i, 1) = Format(DataA(i, 1), FormatA(i, 1))
        End If

        For j = 2 To NumCells
            If DataA(i, j) <> "" Then
                TextA2(i, 1) = TextA2(i, 1) & Separate & Format(DataA(i, j), FormatA(i, j))
            End If
        Next j
    Next i
    TextStringA = TextA2
End Function


Function MMult(Mat1 As Variant, Mat2 As Variant) As Variant
    Dim NumRows1 As Long, NumRows2 As Long, NumCols1 As Long, NumCols2 As Long
    Dim i As Long, j As Long, k As Long, Resa() As Double


    NumRows1 = UBound(Mat1)
    NumRows2 = UBound(Mat2)
    NumCols1 = UBound(Mat1, 2)
    NumCols2 = UBound(Mat2, 2)

    ReDim Resa(1 To NumRows1, 1 To NumCols2)

    If NumCols1 <> NumRows2 Then
        MMult = "Invalid array sizes"
        Exit Function
    End If

    For i = 1 To NumRows1
        For j = 1 To NumCols2
            For k = 1 To NumRows2
                Resa(i, j) = Resa(i, j) + Mat1(i, k) * Mat2(k, j)
            Next k
        Next j
    Next i

    If NumRows1 + NumCols2 = 2 Then
        MMult = Resa(1, 1)
    Else
        MMult = Resa
    End If
End Function
