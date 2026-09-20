Attribute VB_Name = "mPYCurves"
Option Explicit
Public Const Pi As Double = 3.14159265358979


Public Function SandAB(DepthRatio As Double) As Variant
Dim SandABA(1 To 1, 1 To 4) As Double, ABData() As Double, MaxDR As Double
Dim Xa() As Double, YA() As Double, i As Long, j As Long, DRA(1 To 2, 1 To 1) As Variant, Resa As Variant
Const NumRows As Long = 11

    ReDim ABData(1 To NumRows, 1 To 5)
    DRA(1, 1) = DepthRatio

    ABData(1, 1) = 0
    ABData(2, 1) = 0.5
    ABData(3, 1) = 1
    ABData(4, 1) = 1.5
    ABData(5, 1) = 2
    ABData(6, 1) = 2.5
    ABData(7, 1) = 3
    ABData(8, 1) = 3.5
    ABData(9, 1) = 4
    ABData(10, 1) = 4.5
    ABData(11, 1) = 5
    ABData(1, 2) = 2.909
    ABData(2, 2) = 2.509
    ABData(3, 2) = 2.145
    ABData(4, 2) = 1.764
    ABData(5, 2) = 1.509
    ABData(6, 2) = 1.273
    ABData(7, 2) = 1.073
    ABData(8, 2) = 0.982
    ABData(9, 2) = 0.88
    ABData(10, 2) = 0.88
    ABData(11, 2) = 0.88
    ABData(1, 3) = 0.709
    ABData(2, 3) = 0.945
    ABData(3, 3) = 1.091
    ABData(4, 3) = 1.127
    ABData(5, 3) = 1.055
    ABData(6, 3) = 1
    ABData(7, 3) = 0.964
    ABData(8, 3) = 0.945
    ABData(9, 3) = 0.9
    ABData(10, 3) = 0.88
    ABData(11, 3) = 0.88
    ABData(1, 4) = 2.203
    ABData(2, 4) = 1.831
    ABData(3, 4) = 1.576
    ABData(4, 4) = 1.237
    ABData(5, 4) = 1.051
    ABData(6, 4) = 0.881
    ABData(7, 4) = 0.712
    ABData(8, 4) = 0.61
    ABData(9, 4) = 0.542
    ABData(10, 4) = 0.5
    ABData(11, 4) = 0.5
    ABData(1, 5) = 0.525
    ABData(2, 5) = 0.712
    ABData(3, 5) = 0.847
    ABData(4, 5) = 0.864
    ABData(5, 5) = 0.814
    ABData(6, 5) = 0.78
    ABData(7, 5) = 0.695
    ABData(8, 5) = 0.61
    ABData(9, 5) = 0.576
    ABData(10, 5) = 0.55
    ABData(11, 5) = 0.55

    MaxDR = ABData(NumRows, 1)
    ReDim Xa(1 To NumRows, 1 To 1)
    ReDim YA(1 To NumRows, 1 To 1)

    If DepthRatio >= MaxDR Then
        For i = 1 To 4
            SandABA(1, i) = ABData(NumRows, i + 1)
        Next i
    Else
        For i = 1 To NumRows
            Xa(i, 1) = ABData(i, 1)
        Next i
        For i = 1 To 4
            For j = 1 To NumRows
                YA(j, 1) = ABData(j, i + 1)
            Next j
            Resa = CSplineA(Xa, YA, DRA)
            SandABA(1, i) = Resa(1, 1)
        Next i

    End If
    SandAB = SandABA

End Function

Function PfEffDepth(SoilData As Variant, EffDepth As Variant, Optional PYTabsA As Variant) As Variant
Dim Cu As Double, Phi As Double, Gammab As Double, Eps50 As Double, SoilType As Long
Dim LoadType As String, WTab As Double, n As Long, Alpha As Double, Beta As Double, K0 As Double, ka As Double
Dim Pf As Double, Pfu As Double, A_s As Double, Bs As Double, DRatio As Double, Ki As Double, Phir As Double
Dim SandABA As Variant, PYTab As Long, PYCol As Long, PYRows As Long
Dim P As Double
Dim Diam As Double, Depth As Double
Const Kj As Double = 0.5

    ' Finds soil Pf at a specified effective depth

    SoilData = GetArray(SoilData)
    If IsMissing(PYTabsA) = False Then PYTabsA = GetArray(PYTabsA)
    Diam = SoilData(1, 1)
    If UCase(SoilData(2, 1)) <> "PY" Then
        Cu = SoilData(2, 1)    '*
        Phi = SoilData(3, 1)    '*
        Gammab = SoilData(4, 1)    '*
        Eps50 = SoilData(5, 1)
        SoilType = SoilData(6, 1)  '*
        Ki = SoilData(7, 1)
        n = SoilData(8, 1)              '*
        If n > 1 Then LoadType = "C" Else LoadType = "S"    '*
        WTab = SoilData(9, 1)    '
        ' Kbi = Ki * Diam
        ' Gamma_x = EffDepth * Gammab
        Depth = SoilData(10, 1)
        If Depth = 0 Then Depth = EffDepth
        ' Cu_x = Cu * EffDepth
        Select Case SoilType

        Case 1
            ' soft to firm clay
            Pf = Cu * Diam * (3 + Gammab * EffDepth / Cu + Kj / Diam * EffDepth)
            Pfu = 9 * Cu * Diam
            If Pf > Pfu Then Pf = Pfu
            '   Y50 = 2.5 * Eps50 * Diam

        Case 2
            ' Stiff Clay

            If Depth > WTab Then
                Pf = 2 * Cu * Diam + Gammab * EffDepth * Diam + 2.83 * Cu * EffDepth
                Pfu = 11 * Cu * Diam
                If Pf > Pfu Then Pf = Pfu
                DRatio = Depth / Diam
                'Y50 = Eps50 * Diam

                If LoadType = "S" Then
                    A_s = 0.6
                    If DRatio < 4 Then A_s = A_s - 0.4 * ((4 - DRatio) / 4) ^ 2

                    Pf = Pf / 2 * (6 * A_s) ^ 0.5 - 0.055 * Pf * 5 ^ 1.25

                Else
                    Pf = Cu * Diam * (3 + Gammab * EffDepth / Cu + Kj / Diam * EffDepth)

                    Pfu = 9 * Cu * Diam
                    If Pf > Pfu Then Pf = Pfu

                End If
            Else
                Pf = Cu * Diam * (3 + Gammab * EffDepth / Cu + Kj / Diam * EffDepth)
                Pfu = 9 * Cu * Diam
                If Pf > Pfu Then Pf = Pfu

            End If


        Case 3
            ' Sand
            If EffDepth <= 0 Then
                P = 0
            Else
                Phir = Phi * Pi / 180
                Alpha = Phir / 2
                Beta = Pi / 4 + Alpha
                K0 = 0.4
                ka = (Tan(Pi / 4 - Alpha)) ^ 2
                Pf = Gammab * EffDepth * ((K0 * EffDepth * Tan(Phir) * Sin(Beta)) / (Tan(Beta - Phir) * Cos(Alpha)) + Tan(Beta) / (Tan(Beta - Phir)) * (Diam + EffDepth * Tan(Beta) * Tan(Alpha)) _
                                          + K0 * EffDepth * Tan(Beta) * (Tan(Phir) * Sin(Beta) - Tan(Alpha)) - ka * Diam)
                Pfu = ka * Diam * Gammab * EffDepth * ((Tan(Beta)) ^ 8 - 1) + K0 * Diam * Gammab * EffDepth * Tan(Phir) * (Tan(Beta)) ^ 4
                If Pfu < Pf Then Pf = Pfu
                SandABA = SandAB(EffDepth / Diam)

                If LoadType = "S" Then
                    A_s = SandABA(1, 1)
                    Bs = SandABA(1, 3)
                Else
                    A_s = SandABA(1, 2)
                    Bs = SandABA(1, 4)
                End If

                Pf = A_s * Pf

            End If

        Case Else
            ' PY624 = "Invalid soil type"
            Exit Function
        End Select
    Else
        PYTab = SoilData(3, 1)
        PYCol = (PYTab - 1) * 2 + 1
        PYRows = UBound(PYTabsA)
        Do While PYTabsA(PYRows, PYCol) = 0
            PYRows = PYRows - 1
        Loop
        Pf = PYTabsA(PYRows, PYCol + 1)


    End If


    PfEffDepth = Pf
End Function

Function PfEffDepthBrent(SoilData As Variant, EffDepth As Double) As Variant
Dim Pf As Double, Target As Double

    ' Finds soil Pf at a specified effective depth

    Pf = PfEffDepth(SoilData, EffDepth)
    Target = SoilData(11, 1)
    PfEffDepthBrent = Pf - Target
End Function

Function PfLimit(SoilData As Variant, EffDepth As Variant) As Variant
Dim Cu As Double, Phi As Double, Gammab As Double, SoilType As Long
Dim LoadType As String, WTab As Double, n As Long, Alpha As Double, Beta As Double, K0 As Double, ka As Double
Dim Pf As Double, A_s As Double, Bs As Double, DRatio As Double, Phir As Double
Dim SandABA As Variant
Dim P As Double
Dim Diam As Double, Depth As Double

    ' Finds soil Pf at a specified effective depth

    SoilData = GetArray(SoilData)
    ' LoadA = GetArray(LoadA)
    Diam = SoilData(1, 1)
    Cu = SoilData(2, 1)    '*
    Phi = SoilData(3, 1)    '*
    Gammab = SoilData(4, 1)    '*
    'Eps50 = SoilData(5, 1)
    SoilType = SoilData(6, 1)  '*
    'Ki = SoilData(7, 1)
    n = SoilData(8, 1)              '*
    If n > 1 Then LoadType = "C" Else LoadType = "S"    '*
    WTab = SoilData(9, 1)    '
    ' Kbi = Ki * Diam
    ' Gamma_x = EffDepth * Gammab
    'Depth = SoilData(10, 1)
    'If Depth = 0 Then Depth = EffDepth
    ' Cu_x = Cu * EffDepth
    Select Case SoilType

    Case 1
        ' soft to firm clay

        PfLimit = 9 * Cu * Diam

    Case 2
        ' Stiff Clay

        If Depth > WTab Then
            Pf = 11 * Cu * Diam

            DRatio = Depth / Diam
            'Y50 = Eps50 * Diam

            If LoadType = "S" Then
                A_s = 0.6
                If DRatio < 4 Then A_s = A_s - 0.4 * ((4 - DRatio) / 4) ^ 2

                PfLimit = Pf / 2 * (6 * A_s) ^ 0.5 - 0.055 * Pf * 5 ^ 1.25

            Else

                PfLimit = 9 * Cu * Diam

            End If
        Else
            PfLimit = 9 * Cu * Diam

        End If


    Case 3
        ' Sand
        If EffDepth <= 0 Then
            P = 0
        Else
            Phir = Phi * Pi / 180
            Alpha = Phir / 2
            Beta = Pi / 4 + Alpha
            K0 = 0.4
            ka = (Tan(Pi / 4 - Alpha)) ^ 2

            Pf = ka * Diam * Gammab * EffDepth * ((Tan(Beta)) ^ 8 - 1) + K0 * Diam * Gammab * EffDepth * Tan(Phir) * (Tan(Beta)) ^ 4

            SandABA = SandAB(EffDepth / Diam)

            If LoadType = "S" Then
                A_s = SandABA(1, 1)
                Bs = SandABA(1, 3)
            Else
                A_s = SandABA(1, 2)
                Bs = SandABA(1, 4)
            End If

            PfLimit = A_s * Pf

        End If

    Case Else
        ' PY624 = "Invalid soil type"
        Exit Function
    End Select




End Function


Function PY(SoilData As Variant, EffDepth As Double, EffDepthg As Double, Y As Double, Pf As Double, Optional KOption As KOpt = COM624, Optional PYTabsA As Variant) As Variant
Dim Diam As Double, Cu As Double, Phi As Double, Gammab As Double, Eps50 As Double, Depth As Double, SoilType As Long
Dim LoadType As String, WTab As Double, n As Long, C As Double, Alpha As Double, Beta As Double, K0 As Double, ka As Double
Dim Xr As Double, Y50 As Double, A_s As Double, Bs As Double, DRatio As Double, Ki As Double, Phir As Double
Dim SandABA As Variant, Yu As Double, Ym As Double, Pu As Double, Pm As Double, Ms As Double, Ns As Double, C_ As Double, Kbi As Double
Dim Yp As Double, j As Long, P As Double, PYXA() As Double, PYYA() As Double, PYTab As Long, PYRows As Long, PYCol As Long, m As Long

Const MinY As Double = 0.0001, Kj As Double = 0.5

    ' Finds soil stiffness (P/Y) at each node

    SoilData = GetArray(SoilData)
    If IsMissing(PYTabsA) = False Then PYTabsA = GetArray(PYTabsA)
    Diam = SoilData(1, 1)
    Y = Abs(Y)
    If UCase(SoilData(2, 1)) <> "PY" Then
        Cu = SoilData(2, 1)    '*
        Phi = SoilData(3, 1)    '*
        Gammab = SoilData(4, 1)    '*
        Eps50 = SoilData(5, 1)
        SoilType = SoilData(6, 1)  '*
        Ki = SoilData(7, 1)
        n = SoilData(8, 1)              '*
        If n > 1 Then LoadType = "C" Else LoadType = "S"    '*
        WTab = SoilData(9, 1)    '
        If KOption = COM624 Then
            Kbi = Ki * EffDepthg
        Else
            Kbi = Ki * Diam
        End If

        ' Gamma_x = EffDepth * Gammab
        Depth = SoilData(10, 1)
        If Depth = 0 Then Depth = EffDepth


        If Y < MinY Then
            PY = Kbi
        Else
            Select Case SoilType
            Case 1

                Y50 = 2.5 * Eps50 * Diam

                If LoadType = "C" Then Xr = 6 / (Gammab / Cu + Kj / Diam)


                P = Pf / 2 * (Y / Y50) ^ (1 / 3)

                If LoadType = "C" And EffDepth < Xr Then
                    If Y > 3 * Y50 Then
                        P = Pf * 0.72 * EffDepth / Xr
                        If Y < 15 * Y50 Then
                            P = Pf * 0.72 * (1 - (1 - EffDepth / Xr) * (Y - Y50 * 3) / (12 * Y50))
                        End If
                    End If
                Else
                    If P > Pf Then P = Pf
                End If

            Case 2
                ' Stiff Clay

                If Depth > WTab Then
                    DRatio = EffDepth / Diam
                    Y50 = Eps50 * Diam

                    If LoadType = "S" Then
                        A_s = 0.6
                        If DRatio < 4 Then A_s = A_s - 0.4 * ((4 - DRatio) / 4) ^ 2

                        Select Case Y
                        Case Is < A_s * Y50
                            P = Pf / 2 * (Y / Y50) ^ 0.5

                        Case Is < 6 * A_s * Y50
                            P = Pf / 2 * (Y / Y50) ^ 0.5 - 0.055 * Pf * (((Y - A_s * Y50) / (A_s * Y50))) ^ 1.25
                        Case Else
                            P = Pf / 2 * (6 * A_s) ^ 0.5 - 0.055 * Pf * 5 ^ 1.25
                            If Y < 18 * A_s * Y50 Then
                                P = P - 0.0625 / Y50 * Pf * (Y - 6 * Y50 * A_s)
                            Else
                                P = P - 0.0625 / Y50 * Pf * (12 * Y50 * A_s)
                            End If

                        End Select


                    Else
                        A_s = 0.3
                        If DRatio < 2 Then A_s = A_s - 0.1 * ((2 - DRatio) / 2) ^ 2
                        Yp = 4.1 * A_s * Y50

                        Select Case Y
                        Case Is < 0.6 * Yp
                            P = A_s * Pf * (1 - Abs((Y - 0.45 * Yp) / (0.45 * Yp)) ^ 2.5)
                        Case Else
                            P = A_s * Pf * (1 - (1 / 3) ^ 2.5)
                            If Y < 1.8 * Yp Then
                                P = P - 0.085 * Pf * (Y - 0.6 * Yp) / Y50
                            Else
                                P = P - 1.2 * Yp * 0.085 * Pf / Y50
                            End If
                        End Select
                    End If
                Else
                    Y50 = Eps50 * Diam * 2.5

                    If Y < 16 * Y50 Then
                        P = Pf / 2 * (Y / Y50) ^ 0.25
                    Else
                        P = Pf
                    End If

                    If LoadType = "C" Then


                        C = 9.6 * (P / Pf) ^ 4
                        P = P * Y / (Y + Y50 * C * Log(n) / Log(10))
                    End If

                End If


            Case 3
                ' Sand
                If EffDepth <= 0 Then
                    P = 0
                Else

                    SandABA = SandAB(Depth / Diam)

                    If LoadType = "S" Then
                        A_s = SandABA(1, 1)
                        Bs = SandABA(1, 3)
                    Else
                        A_s = SandABA(1, 2)
                        Bs = SandABA(1, 4)
                    End If

                    Yu = 3 * Diam / 80
                    Pu = Pf    ' A_s * Pf
                    Ym = Diam / 60
                    Pm = Bs * Pu / A_s
                    Ms = (Pf - Pm) / (Yu - Ym)
                    Ns = Pm / (Ms * Ym)
                    C_ = Pm / (Ym ^ (1 / Ns))

                    P = C_ * Y ^ (1 / Ns)

                    If P > Pm Then P = Pm + (Y - Ym) * Ms
                    If P > Pu Then P = Pu

                End If

            Case Else
                PY = "Invalid soil type"
                Exit Function
            End Select
            PY = P / Y

            If (SoilType = 2 And Kbi > 0) Or SoilType = 3 Then
                If PY > Kbi Then PY = Kbi

            End If
        End If
    Else
        PYTab = SoilData(3, 1)
        PYCol = (PYTab - 1) * 2 + 1
        PYRows = UBound(PYTabsA)
        Do While PYTabsA(PYRows, PYCol) = 0
            PYRows = PYRows - 1
        Loop


        ReDim PYXA(1 To PYRows, 1 To 1)
        ReDim PYYA(1 To PYRows, 1 To 1)
        PYCol = (PYTab - 1) * 2 + 1

        For m = 2 To PYRows
            If PYTabsA(m, 1) = 0 Then Exit For
            PYXA(m, 1) = PYTabsA(m, PYCol)
            PYYA(m, 1) = PYTabsA(m, PYCol + 1)
        Next m

        If Y <= PYXA(2, 1) Then
            Y = PYXA(2, 1)
            P = PYYA(2, 1)
        Else
            P = CSplineA(PYXA, PYYA, Y, 1)(1, 1)
        End If
        PY = P / Y
    End If

End Function

Public Function GetArray(Arrayname As Variant) As Variant
Dim TempA() As Variant, LBound1 As Long, UBound1 As Long, UBound2 As Long
Dim i As Long, j As Long

    ' This function converts a single or muti-cell range into an array, and
    ' converts a 1D array into single row or single column 2D base 1 array

    ' If Arrayname is not an array, convert it into one.
    ' IsArray is true for multi-cell ranges, but not for a single cell range
    If Not IsArray(Arrayname) Then
        Arrayname = Array(Arrayname)
    End If

    ' If Arrayname is a range, convert it into an array containing the range cell values
    If TypeName(Arrayname) = "Range" Then
        GetArray = Arrayname.Value
        'Otherwise simply allocate the array to GetArray
    Else
        GetArray = Arrayname
    End If

    ' Check for a 1D array, or a base 0 array
    On Error Resume Next
    UBound2 = UBound(GetArray, 2)
    ' Convert to base 1
    If UBound2 = 0 Then
        LBound1 = LBound(GetArray)
        UBound1 = UBound(GetArray)
        ReDim TempA(1 To 1, 1 To UBound1 - LBound1 + 1)
        j = 1
        For i = LBound1 To UBound1
            TempA(1, j) = Arrayname(i)
            j = j + 1
        Next i

        GetArray = TempA
    End If

End Function


Function PY_624(SoilData As Variant, Y_A As Variant, LoadA As Variant, Optional PYTabsA As Variant, Optional KOption As Long = 1) As Variant
Dim Diam As Double, Depth As Double, SoilType As Long, NumNodes As Long, NumSoil As Long
Dim Pf As Double, PYA() As Double, i As Long, Ki As Double
Dim Kbi As Double
Dim Y As Double, j As Long, P As Double, PYXA() As Double, PYYA() As Double, PYTab As Long, PYRows As Long, PYCol As Long, m As Long
Dim Gamma_x As Double, EffDepth As Double, EffDepthg As Double, CurrLayer As Long, Pftop As Double, SoilAJ(1 To 17, 1 To 1) As Variant, k As Long, Maxdepth As Double
Dim TopEffDepth As Variant, TopDepth As Double, DepthAdj As Double, YA As Variant, PfMax As Double, Proj As Double, PYRows2 As Long, EffDepthA() As Double
Dim CalcEffDepthW As Boolean, CalcEffDepthKi As Boolean
Const MinY As Double = 0.000001

    ' Finds soil stiffness (P/Y) at each node

    SoilData = GetArray(SoilData)
    YA = GetArray(Y_A)
    If IsMissing(PYTabsA) = False Then
        PYTabsA = GetArray(PYTabsA)
        PYRows = UBound(PYTabsA)
    End If
    NumSoil = UBound(SoilData, 2)
    For j = NumSoil To 1 Step -1
        If SoilData(1, j) > 0 Then Exit For
    Next j
    NumSoil = j
    ReDim EffDepthA(1 To NumSoil, 1 To 4)

    NumNodes = UBound(YA)
    ReDim PYA(1 To NumNodes, 1 To 6)
    Maxdepth = SoilData(1, NumSoil) * 10
    SoilAJ(8, 1) = LoadA(6, 1)
    SoilAJ(9, 1) = LoadA(7, 1)


    j = 1
    CurrLayer = 1
    Gamma_x = 0

    ' Generate table of effdepth, effdepthg at top of layer, for each layer
    EffDepthA(1, 1) = 0
    EffDepthA(1, 2) = 0

    CalcEffDepthW = False
    CalcEffDepthKi = False
    If UBound(SoilData) > 7 Then
        If SoilData(8, NumSoil) <> Empty Then CalcEffDepthW = True
        If UBound(SoilData) > 8 Then
            If SoilData(9, NumSoil) <> Empty Then CalcEffDepthKi = True
        End If
    End If

    If CalcEffDepthKi = True Then
        For i = 2 To NumSoil
            EffDepthA(i, 2) = SoilData(9, i)
        Next i
    Else
        If NumSoil > 1 Then EffDepthA(2, 2) = (EffDepthA(1, 2) + SoilData(1, 1)) * SoilData(4, 1) / SoilData(4, 2)
        For i = 3 To NumSoil
            EffDepthA(i, 2) = (EffDepthA(i - 1, 2) + (SoilData(1, i - 1) - SoilData(1, i - 2))) * SoilData(4, i - 1) / SoilData(4, i)
        Next i
    End If

    If CalcEffDepthW = True Then
        For i = 1 To NumSoil
            EffDepthA(i, 1) = SoilData(8, i)
        Next i
    Else
        For i = 2 To NumSoil

            Depth = SoilData(1, i - 1)
            j = 1
            Do While YA(j, 1) < Depth And j < NumNodes
                j = j + 1
            Loop
            Diam = YA(j, 2)
            SoilAJ(1, 1) = Diam

            For k = 2 To 7
                SoilAJ(k, 1) = SoilData(k, i - 1)
            Next k


            SoilAJ(10, 1) = Depth

            If UCase(SoilData(2, i - 1)) = "PY" Then
                PYTab = SoilData(3, i - 1)
                PYCol = (PYTab - 1) * 2 + 1
                PYRows2 = PYRows
                Do While PYTabsA(PYRows2, PYCol) = 0
                    PYRows2 = PYRows2 - 1
                Loop
                Pftop = PYTabsA(PYRows2, PYCol + 1)
            End If
            If i = 2 Then
                EffDepth = EffDepthA(i - 1, 1) + SoilData(1, i - 1)
            Else
                EffDepth = EffDepthA(i - 1, 1) + (SoilData(1, i - 1) - SoilData(1, i - 2))
            End If
            If UCase(SoilData(2, i - 1)) = "PY" Then
                Pftop = PfEffDepth(SoilAJ, EffDepth, PYTabsA)
            Else
                Pftop = PfEffDepth(SoilAJ, EffDepth)
            End If
            EffDepthA(i, 3) = Pftop

            If UCase(SoilData(2, i)) <> "PY" Then
                For k = 2 To 7
                    SoilAJ(k, 1) = SoilData(k, i)
                Next k
                PfMax = PfLimit(SoilAJ, Depth)
                If Pftop < PfMax Then
                    SoilAJ(11, 1) = Pftop
                    TopEffDepth = QuadBrent("pfeffdepthbrent", 0, Maxdepth, SoilAJ)
                    If IsArray(TopEffDepth) = True Then
                        DepthAdj = TopEffDepth(1, 1) - Depth
                    Else
                        DepthAdj = EffDepthA(i, 2) - Depth
                    End If
                Else
                    DepthAdj = EffDepthA(i, 2) - Depth
                End If
            End If
            EffDepthA(i, 1) = Depth + DepthAdj
            EffDepthA(i, 4) = PfMax
        Next i

    End If

    j = 1
    For i = 1 To NumNodes
        Diam = YA(i, 2)
        SoilAJ(1, 1) = Diam
        Depth = YA(i, 1)
        'Find soil layer number
        Do While SoilData(1, j) <= Depth And j < NumSoil
            j = j + 1
        Loop

        PYA(i, 2) = j
        If UCase(SoilData(2, j)) = "PY" Then
            SoilAJ(2, 1) = "PY"
            SoilAJ(3, 1) = SoilData(3, j)


        End If
        If j = 1 Then
            If (SoilData(4, 1) = 0 Or SoilData(6, 1) = 0) And SoilData(2, j) <> "PY" Then
                PYA(i, 3) = 0
                PYA(i, 4) = 0
            Else
                PYA(i, 3) = Depth
                PYA(i, 4) = Depth
                EffDepth = PYA(i, 3)
                EffDepthg = PYA(i, 4)
            End If
            ' GoTo Next_i
        Else
            EffDepth = EffDepthA(j, 1) + Depth - SoilData(1, j - 1)
            EffDepthg = EffDepthA(j, 2) + Depth - SoilData(1, j - 1)
            PYA(i, 3) = EffDepth
            PYA(i, 4) = EffDepthg
        End If
        If UCase(SoilData(2, j)) = "PY" Then GoTo FindPY

        SoilAJ(1, 1) = Diam
        For k = 2 To 7
            SoilAJ(k, 1) = SoilData(k, j)
        Next k
        SoilAJ(10, 1) = Depth
        Ki = SoilData(7, j)

        If KOption = kDiam Then
            Kbi = Ki * Diam
        Else
            Kbi = Ki * EffDepthg
        End If
FindPY:
        Y = Abs(YA(i, 3))

        If Y < MinY And UCase(SoilData(2, j)) <> "PY" Then
            PYA(i, 1) = Kbi
        Else
            If UCase(SoilData(2, j)) = "PY" Then
                Pf = PfEffDepth(SoilAJ, EffDepth, PYTabsA)
            Else
                Pf = PfEffDepth(SoilAJ, EffDepth)
            End If

            PYA(i, 5) = Pf
            If Pf = 0 Then
                PYA(i, 1) = 0
            Else
                If UCase(SoilData(2, j)) = "PY" Then
                    PYA(i, 1) = PY(SoilAJ, EffDepth, EffDepthg, Y, Pf, KOption, PYTabsA)
                Else
                    PYA(i, 1) = PY(SoilAJ, EffDepth, EffDepthg, Y, Pf, KOption)
                End If
            End If
        End If
Next_i:
        PYA(i, 6) = PYA(i, 1) * YA(i, 3)
    Next i

    PY_624 = PYA
End Function

Function PY624tab(SoilData As Variant, PileSect As Variant, LoadA As Variant, YA As Variant, _
                  Optional KOption As KOpt = COM624) As Variant
Dim Diam As Double, Cu As Double, Phi As Double, Gammab As Double, Eps50 As Double, Depth As Double, SoilType As Long, LinLimits() As Double
Dim LoadType As String, WTab As Double, n As Long, C As Double, Alpha As Double, Beta As Double, K0 As Double, ka As Double
Dim Xr As Double, Pf As Double, Pfu As Double, Y50 As Double, Stepinc As Double, PYA() As Double, i As Long, A_s As Double, Bs As Double, DRatio As Double, Ki As Double, Phir As Double
Dim SandABA As Variant, Yu As Double, Ym As Double, Pu As Double, Pm As Double, Ms As Double, Ns As Double, C_ As Double, Kbi As Double, NumSoil As Long, j As Long
Dim k As Long, NumSect As Long, Gamma_x As Double, pf_2 As Double, NumNodes As Long, SoilAJ(1 To 10, 1 To 1) As Variant
Dim EffDepth As Double, EffDepthg As Double, Y As Double
Const Kj As Double = 0.5


    ' Create PY curve for Specified effective depths and elastic and plastic limits (bottom row)

   ' If MinSteps = 0 Then MinSteps = 12
    SoilData = GetArray(SoilData)
    PileSect = GetArray(PileSect)
    LoadA = GetArray(LoadA)
    YA = GetArray(YA)
    NumNodes = UBound(YA)

    ' NumSoil = UBound(SoilData, 2)
    NumSect = UBound(PileSect, 2)
    ReDim PYA(1 To NumNodes, 1 To 1)
    ' ReDim LinLimits(1 To NumNodes + 1, 1 To 4)
    EffDepth = SoilData(8, 1)
    EffDepthg = SoilData(9, 1)
    
    SoilAJ(1, 1) = PileSect(2, 1)
    For i = 2 To 7
    SoilAJ(i, 1) = SoilData(i, 1)
    Next i
    SoilAJ(8, 1) = LoadA(6, 1)
    SoilAJ(9, 1) = LoadA(7, 1)
    SoilAJ(10, 1) = SoilData(1, 1)
    
    
    
Pf = PfEffDepth(SoilAJ, EffDepth)
    For i = 1 To NumNodes
    Y = Abs(YA(i, 1))
       If Y > 0 Then
       PYA(i, 1) = PY(SoilAJ, EffDepth, EffDepthg, Y, Pf, KOption) * Y
        Else
        PYA(i, 1) = 0
        End If
        
        Next i
    PY624tab = PYA
End Function






