Attribute VB_Name = "mSolveFunc"
Option Explicit

Private Const gMaxIts As Long = 200

Function QuadBrent(Func As String, ByVal Ak As Double, ByVal bk As Double, Coefficients As Variant, _
                   Optional YTol As Double = 0.00000000000001, Optional MaxIts As Long = gMaxIts, _
                   Optional Subr As Long = 1, Optional XTol As Double = 0.0000000001) As Variant
    Dim Ck As Double, Sk As Double, Dk As Double, XRange As Double
    Dim Yak As Double, Ybk As Double, Yck As Double, Ysk As Double, Ydk As Double
    Dim i As Long, LastStepB As Boolean, Temp As Double, Resa(1 To 3, 1 To 1) As Double, SubName As String

    If TypeName(Coefficients) = "Range" Then Coefficients = Coefficients.Value2

    Yak = Application.Run(Func, Coefficients, Ak)
    Ybk = Application.Run(Func, Coefficients, bk)

    If (Yak < 0 And Ybk < 0) Or (Yak > 0 And Ybk > 0) Then
        QuadBrent = "Yak and Ybk must have different signs"
        Exit Function
    End If

    If Abs(Yak) < Abs(Ybk) Then
        Temp = Ak
        Ak = bk
        bk = Temp
        Temp = Yak
        Yak = Ybk
        Ybk = Temp
    End If

    Ck = Ak
    Yck = Yak
    LastStepB = True

    For i = 1 To MaxIts

        XRange = (bk - Ak)


        If (Abs(Ybk) < YTol) Then Exit For

        If Yak <> Yck And Ybk <> Yck Then

            ' SolveInvQuad uses inverse quadratic interpolation, SolveQuad uses Mullers method of quadratic interpolation
            If Subr = 1 Then SubName = "solveInvQuad" Else SubName = "solveQuad"
            Sk = Application.Run(SubName, Ak, Yak, bk, Ybk, Ck, Yck)    '

        Else
            Sk = bk - (Ybk) * (bk - Ak) / (Ybk - Yak)
        End If

        If ((Sk - (3 * Ak + bk) / 4) * (Sk - bk)) > 0 Then
            Sk = (Ak + bk) / 2
            LastStepB = True
        ElseIf LastStepB = True Then
            If Abs(Sk - bk) >= Abs(bk - Ck) / 2 Or (Abs(bk - Ck) < Abs(XTol)) Then
                Sk = (Ak + bk) / 2
                LastStepB = True
            Else
                LastStepB = False
            End If
        ElseIf Abs(Sk - bk) >= Abs(Ck - Dk) / 2 Or Abs(Ck - Dk) < Abs(XTol) Then
            Sk = (Ak + bk) / 2
            LastStepB = True
        Else
            LastStepB = False
        End If

        ' Use Application.run to evaluate Func for the value Sk
        Ysk = Application.Run(Func, Coefficients, Sk)
        '----------------------------------------
        Dk = Ck
        Ydk = Yck
        Ck = bk
        Yck = Ybk

        If Yak * Ysk < 0 Then
            bk = Sk
            Ybk = Ysk
        Else
            Ak = Sk
            Yak = Ysk
        End If
        If Abs(Yak) < Abs(Ybk) Then
            Temp = Ak
            Ak = bk
            bk = Temp
            Temp = Yak
            Yak = Ybk
            Ybk = Temp
        End If

    Next i

    If Abs(Ybk) < Abs(Ysk) Then
        Resa(1, 1) = bk
        Resa(3, 1) = Ybk
    Else:
        Resa(1, 1) = Sk
        Resa(3, 1) = Ysk
    End If
    Resa(2, 1) = i - 1

    QuadBrent = Resa
End Function

Function QuadMuller(Func As String, ByVal Ak As Double, ByVal bk As Double, Coefficients As Variant, Optional maxErr As Double = 0.00000000000001, Optional MaxIts As Long = 20) As Variant
    Dim Ck As Variant, YRange As Double, NormErr As Double
    Dim i As Long, QSlope As Long, X As Double, Y As Double, Yak As Double, Ybk As Double, Yck As Double, Xa(1 To 3, 1 To 10) As Double

    If TypeName(Coefficients) = "Range" Then Coefficients = Coefficients.Value2

    Ck = (Ak + bk) / 2

    Yak = Application.Run(Func, Coefficients, Ak)
    Ybk = Application.Run(Func, Coefficients, bk)
    Yck = Application.Run(Func, Coefficients, Ck)

    YRange = Ybk - Yak
    NormErr = 1
    If YRange / (Ak - bk) > 0 Then QSlope = 1 Else QSlope = -1

    For i = 1 To MaxIts
        X = SolveQuad(Ak, Yak, Ck, Yck, bk, Ybk)
        If X <> xlErrNA Then

            Y = Application.Run(Func, Coefficients, X)

            NormErr = Abs((Y) / YRange)
            If NormErr <= maxErr Then Exit For

            If Abs(X - bk) > Abs(X - Ak) Then
                bk = Ck
                Ybk = Yck
            Else
                Ak = Ck
                Yak = Yck
            End If
            Ck = X
            Yck = Y
        Else
            QuadMuller = CVErr(xlErrNA)
            Exit Function
        End If

    Next i
    Xa(1, 1) = X
    Xa(2, 1) = i
    Xa(3, 1) = NormErr

    QuadMuller = Xa
End Function

Function QuadSolve2(Func As String, Pointdata As Variant, Coefficients As Variant, Optional maxErr As Double = 0.00000000000001, Optional MaxIts As Long = gMaxIts) As Variant
    Dim MinX As Variant, MidX As Double, MaxX As Variant, YRange As Double, NormErr As Double
    Dim i As Long, X As Double, Y As Double, MinY As Double, MidY As Double, MaxY As Double, Xa(1 To 3, 1 To 10) As Double

    If TypeName(Pointdata) = "Range" Then Pointdata = Pointdata.Value2
    If TypeName(Coefficients) = "Range" Then Coefficients = Coefficients.Value2

    MinX = Pointdata(1, 1)
    MidX = Pointdata(2, 1)
    MaxX = Pointdata(3, 1)

    MinY = Pointdata(1, 2)
    MidY = Pointdata(2, 2)
    MaxY = Pointdata(3, 2)
    YRange = MaxY - MinY
    NormErr = 1


    For i = 1 To MaxIts

        X = MidY * MaxY * MinX / ((MinY - MidY) * (MinY - MaxY)) _
          + MinY * MaxY * MidX / ((MidY - MinY) * (MidY - MaxY)) _
          + MinY * MidY * MaxX / ((MaxY - MinY) * (MaxY - MidY))

        Y = Application.Run(Func, Coefficients, X)

        NormErr = Abs(Y / YRange)
        If NormErr <= maxErr Then Exit For

        If Abs(Y - MaxY) > Abs(Y - MinY) Then


            MaxX = MidX
            MaxY = MidY
            Pointdata(3, 1) = MaxX
            Pointdata(3, 2) = MaxY
        Else
            MinX = MidX
            MinY = MidY
            Pointdata(1, 1) = MinX
            Pointdata(1, 2) = MinY
        End If
        MidX = X
        MidY = Y
        Pointdata(2, 1) = MidX
        Pointdata(2, 2) = MidY

    Next i
    Xa(1, 1) = X
    Xa(2, 1) = i
    Xa(3, 1) = NormErr


    QuadSolve2 = Xa
End Function


Function FitQuad(Pointdata As Variant) As Variant
    Dim CoeffA(1 To 3, 1 To 1) As Double
    Dim x1 As Double, y1 As Double, x2 As Double, y2 As Double, X3 As Double, Y3 As Double
    Dim A As Double, B As Double, C As Double

    If TypeName(Pointdata) = "Range" Then Pointdata = Pointdata.Value2

    x1 = Pointdata(1, 1)
    y1 = Pointdata(1, 2)
    x2 = Pointdata(2, 1)
    y2 = Pointdata(2, 2)
    X3 = Pointdata(3, 1)
    Y3 = Pointdata(3, 2)

    A = ((y2 - y1) * (x1 - X3) + (Y3 - y1) * (x2 - x1)) / ((x1 - X3) * (x2 ^ 2 - x1 ^ 2) + (x2 - x1) * (X3 ^ 2 - x1 ^ 2))
    B = ((y2 - y1) - A * (x2 ^ 2 - x1 ^ 2)) / (x2 - x1)
    C = y1 - A * x1 ^ 2 - B * x1

    CoeffA(1, 1) = A
    CoeffA(2, 1) = B
    CoeffA(3, 1) = C

    FitQuad = CoeffA

End Function

Function Quadratic2(A, B, C) As Variant
    Dim QuadResA(1 To 2, 1 To 1) As Double
    Dim disc As Double

    disc = B ^ 2 - 4 * A * C

    If disc >= 0 Then
        If A > 0 Then
            QuadResA(1, 1) = (-B - (disc) ^ 0.5) / (2 * A)
            QuadResA(2, 1) = (-B + (disc) ^ 0.5) / (2 * A)
        ElseIf A < 0 Then
            QuadResA(2, 1) = (-B - (disc) ^ 0.5) / (2 * A)
            QuadResA(1, 1) = (-B + (disc) ^ 0.5) / (2 * A)
        End If
    Else
        QuadResA(1, 1) = (xlErrNA)
    End If
    Quadratic2 = QuadResA
End Function




Function SolveInvQuad(x1, y1, x2, y2, X3, Y3) As Double

    SolveInvQuad = (-y2) * (-Y3) * x1 / ((y1 - y2) * (y1 - Y3)) _
                 + (-y1) * (-Y3) * x2 / ((y2 - y1) * (y2 - Y3)) _
                 + (-y1) * (-y2) * X3 / ((Y3 - y1) * (Y3 - y2))

End Function

Function SolveQuad(x1, y1, x2, y2, X3, Y3) As Variant
    Dim Fk32 As Double, Fk31 As Double, Fk21 As Double, Fk321 As Double, W As Double, v As Double, D As Double, E As Double
    ' Mullers method: http://en.wikipedia.org/wiki/Muller%27s_method

    Fk32 = (Y3 - y2) / (X3 - x2)
    Fk31 = (Y3 - y1) / (X3 - x1)
    Fk21 = (y2 - y1) / (x2 - x1)
    Fk321 = (Fk21 - Fk32) / (x1 - X3)

    W = Fk32 + Fk31 - Fk21
    v = (W ^ 2 - 4 * Y3 * Fk321) ^ 0.5
    D = W - v
    E = W + v
    If Abs(E) > Abs(D) Then D = E

    SolveQuad = X3 - (2 * Y3) / D

End Function

Function ResE(ParamA As Variant, X As Double) As Double
    Dim A1 As Double, A2 As Double, Q1 As Double, Q2 As Double, i1 As Double, I2 As Double
    Dim B1 As Double, k As Double, Dt As Double, Dc1 As Double, I1c As Double, E As Double

    A1 = ParamA(1, 1)
    B1 = ParamA(2, 1)
    k = ParamA(3, 1)
    Dt = ParamA(4, 1)
    Dc1 = ParamA(5, 1)
    I1c = ParamA(6, 1)
    E = ParamA(7, 1)

    A2 = (B1 + k * (X - Dt) / 2) * (X - Dt)
    Q1 = A1 * (X - Dc1)
    Q2 = A2 * ((3 * B1 + 2 * k * (X - Dt))) / ((2 * B1 + k * (X - Dt))) * (X - Dt) / 3
    i1 = I1c + A1 * (X - Dc1) ^ 2
    I2 = (X - Dt) ^ 3 * (4 * B1 + 3 * k * (X - Dt)) / 12

    ResE = ((i1 + I2) / (Q1 + Q2) - X) - E
End Function






