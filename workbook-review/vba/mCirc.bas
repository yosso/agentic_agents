Attribute VB_Name = "mCirc"
Option Explicit
Private Const MinD As Double = 0.000001

Public Function CircE(Sect As Variant, axial As Double, Moment As Double, Out1 As Long, Optional Out2 As Double = 0.5) As Variant
    Dim Xa As Variant, Y As Double, YA As Variant, ZTop As Double, QComp As Double, Icomp As Double, CArea As Double, Acomp As Double, MR As Double, CMR As Double, Loads(1 To 2, 1 To 1) As Variant
    Dim ConcR As Double, Ec As Double, Reod As Double, ReoR As Double, NumReo As Long, ReoCov As Double, Es As Double, Ecc As Double, Ast As Double, Qconc As Double, QNARnf As Double
    Dim BarArea As Double, Sigct As Double, Momin As Double, Axin As Double, Mome As Double, LayerA() As Double, SectData(1 To 12) As Variant, StrainA(1 To 6, 1 To 1) As Double
    Dim StressFact As Double, AConc As Double, Irnf As Double, Iconc As Double, StressA(1 To 4, 1 To 1), Res2A(1 To 12, 1 To 1) As Double, Res3A As Variant, ReoCent As Double, Sigcb As Double
    Dim i As Long, YMin As Double, YMax As Double, Func As String, ReoStat As Long, NALAyer As Long, Ireo As Double, Iucomp As Double, Aucomp As Double, ZMResA(1 To 2, 1 To 1) As Double

    If TypeName(Sect) = "Range" Then Sect = Sect.Value2

    Loads(1, 1) = axial
    Loads(2, 1) = Moment
    Momin = Moment * 1000000
    Axin = axial * 1000
    ConcR = Sect(1, 1) / 2
    If Axin <> 0 Then Ecc = Momin / Axin - ConcR Else Ecc = 1000000000#

    CArea = Pi * ConcR ^ 2
    Ec = Sect(8, 1)
    Reod = Sect(2, 1)
    ReoR = Reod / 2
    BarArea = ReoR ^ 2 * Pi
    NumReo = Sect(3, 1)
    ReoCov = Sect(4, 1)
    Es = Sect(7, 1)
    MR = Es / Ec
    CMR = MR - 1

    ' Find reinforcement area properties
    If ReoStat = 0 Then
        ReoStat = CircReoLayers(Sect, LayerA, Ireo)
    End If

    ' Section properties of uncracked section
    Iucomp = Pi * ConcR ^ 4 / 4 + LayerA(NumReo / 2 + 2, 6)
    Aucomp = CArea + BarArea * NumReo * CMR
    Y = ConcR

    If Abs(Momin) >= 100000 Then
        ' Find layer containing Neutral Axis
        NALAyer = CircNALayer(Sect, Loads, LayerA)

        SectData(1) = 1
        SectData(2) = Sect(1, 1) / 2

        ' Find depth of Neutral Axis
        ' If NA is outside the concrete section use MoverZC
        ' If axial load = 0 use CircNA0
        ' Otherwise use QuadBrent and CircleQxoI
        If NALAyer = 0 Or NALAyer > NumReo / 2 + 2 Then
            Xa = MoverZC(Sect, LayerA, Loads, NALAyer, StressA)
            Y = Xa(1, 1)
        Else
            If Abs(Axin) <> 0 Then
                i = NALAyer
                SectData(1) = ConcR
                SectData(2) = LayerA(i, 3)
                SectData(3) = LayerA(i, 4)
                SectData(4) = LayerA(i, 6)
                SectData(5) = Ecc
                SectData(6) = 1
                YMin = LayerA(i, 1)
                YMax = LayerA(i, 2)
                Func = "circleqxoi"
                YA = QuadBrent(Func, YMin, YMax, SectData)
                Y = YA(1, 1)
                SectData(6) = 2
                Xa = CircleQxoI(SectData, Y)
            Else
                Xa = CircNA0(SectData, NALAyer, LayerA)
                Y = Xa(1, 1)
            End If
        End If

        ReoCent = LayerA(2, 1)
        QComp = Xa(7, 1) + Xa(8, 1)
        Icomp = Xa(2, 1) + Xa(3, 1)

        AConc = Xa(4, 1)
        Ast = Xa(5, 1)
        Acomp = Xa(6, 1)
        Qconc = Xa(7, 1)
        QNARnf = Xa(8, 1)

        Irnf = Xa(3, 1)
        Iconc = Xa(2, 1)


        If Y > MinD And Y < Sect(1, 1) Then
            ZTop = Icomp / Y
            Mome = Momin + Axin * (Y - ConcR)
            If ZTop <> 0 Then Sigct = Mome / ZTop
            StressFact = Sigct / Y
        Else
            ZTop = Icomp / ConcR
            If ZTop <> 0 Then Sigct = (Axin / Acomp + Momin / ZTop)
            If ZTop <> 0 Then Sigcb = (Axin / Acomp - Momin / ZTop)
            StressFact = -(Sigcb - Sigct) / Sect(1, 1)
        End If
    Else

        ZMResA(1, 1) = Aucomp
        ZMResA(2, 1) = Iucomp
        CircE = ZMResA
        Exit Function
    End If
    Select Case Out1
    Case 0
        CircE = Xa
        Exit Function

    Case 1

        Res2A(1, 1) = Sigct
        Res2A(2, 1) = (Sigct - StressFact * ReoCent) * MR
        Res2A(3, 1) = (Sigct - StressFact * (Sect(1, 1) - ReoCent)) * MR
        Res2A(4, 1) = Sigcb

    Case 2

        Res2A(1, 1) = Sigct / Ec
        Res2A(2, 1) = Res2A(1, 1) * (1 - ReoCent / Y)
        Res2A(3, 1) = Res2A(1, 1) * (1 - (Sect(1, 1) - ReoCent) / Y)
        Res2A(4, 1) = Res2A(1, 1) * (1 - Sect(1, 1) / Y)

    Case 3
        Res2A(1, 1) = Qconc * StressFact / 1000
        Res2A(2, 1) = QNARnf * StressFact / 1000
        Res2A(3, 1) = QComp * StressFact / 1000

    Case 4
        If Y > MinD And Y < ConcR Then
            Res2A(1, 1) = (Iconc + Qconc * (ConcR - Y)) * StressFact / 1000000
            Res2A(2, 1) = (Irnf + QNARnf * (ConcR - Y)) * StressFact / 1000000
            Res2A(3, 1) = (Icomp + QComp * (ConcR - Y)) * StressFact / 1000000
        Else
            Res2A(1, 1) = (Iconc) * StressFact / 1000000
            Res2A(2, 1) = (Irnf) * StressFact / 1000000
            Res2A(3, 1) = (Icomp) * StressFact / 1000000
        End If
    Case 5
        Res2A(1, 1) = Y
        Res2A(2, 1) = Acomp
        Res2A(3, 1) = QComp
        Res2A(4, 1) = Icomp
        Res2A(5, 1) = AConc
        Res2A(6, 1) = Ast
        Res2A(7, 1) = Qconc
        Res2A(8, 1) = QNARnf
        Res2A(9, 1) = Iconc
        Res2A(10, 1) = Irnf
        Res2A(11, 1) = Y - QComp / Acomp

    Case 6
        StrainA(1, 1) = Y
        StrainA(2, 1) = Sigct / Ec
        StrainA(3, 1) = StrainA(2, 1) * (1 - ReoCent / Y)
        StrainA(4, 1) = StrainA(2, 1) * (1 - (Sect(1, 1) - ReoCent) / Y)
        StrainA(5, 1) = StrainA(2, 1) * (1 - Sect(1, 1) / Y)
        StrainA(6, 1) = Y - QComp / Acomp
        Res3A = CircCrack(Sect, Loads, Irnf, StrainA, 2, Out2, Iucomp)
    End Select

    If Out1 = 6 Then
        CircE = Res3A
    Else
        CircE = Res2A
    End If

End Function


Function CircReoLayers(Sect As Variant, LayerA() As Double, ByRef Ireo As Double) As Variant
    Dim ConcR As Double, Ec As Double, Reod As Double, ReoR As Double, NumReo As Long, ReoCov As Double, Es As Double, Ecc As Double, Momin As Double, Axin As Double
    Dim i As Long, Nlayers As Long, Ang As Double, Anginc As Double, ReoArc As Double
    Dim CArea As Double, MR As Double, CMR As Double, BarArea As Double, BarsPerRow As Long
    Dim Yr As Double, Iyr As Double

    If TypeName(Sect) = "Range" Then Sect = Sect.Value2

    ConcR = Sect(1, 1) / 2

    If Axin <> 0 Then Ecc = Momin / Axin - ConcR Else Ecc = 1000000000#


    CArea = Pi * ConcR ^ 2
    Ec = Sect(8, 1)
    Reod = Sect(2, 1)
    ReoR = Reod / 2
    BarArea = ReoR ^ 2 * Pi
    NumReo = Sect(3, 1)
    ReoCov = Sect(4, 1)
    Es = Sect(7, 1)
    ReoArc = ConcR - ReoCov - ReoR
    MR = Es / Ec
    CMR = MR - 1

    Nlayers = (Int(NumReo / 2) + 2)
    Anginc = Pi / (Nlayers - 2)
    ReDim LayerA(1 To Nlayers, 1 To 6)
    ' 1 Top depth, 2 bottom depth, 3 Reo Area, 4 Y Cent, 5 Qreo, 6 IReo
    Ang = 0

    BarsPerRow = 1
    LayerA(1, 1) = 0
    LayerA(1, 2) = ConcR - ReoArc
    LayerA(1, 3) = BarArea * NumReo * MR
    LayerA(1, 4) = 0
    Yr = ConcR - LayerA(1, 2)
    LayerA(1, 5) = LayerA(1, 3) * (LayerA(1, 4) - Yr)
    Iyr = BarArea * MR * Yr ^ 2 * BarsPerRow

    For i = 2 To Nlayers - 1
        Ang = Ang + Anginc
        LayerA(i, 1) = LayerA(i - 1, 2)
        LayerA(i, 2) = ConcR - ReoArc * Cos(Ang)
        Yr = ConcR - LayerA(i, 2)
        LayerA(i, 3) = LayerA(i - 1, 3) - BarArea * BarsPerRow
        LayerA(i, 4) = (LayerA(i - 1, 4) * LayerA(i - 1, 3) - BarArea * BarsPerRow * ((ConcR - LayerA(i, 1)))) / LayerA(i, 3)
        LayerA(i, 5) = LayerA(i, 3) * (LayerA(i, 4) - Yr)
        Iyr = Iyr + BarArea * 2 * MR * Yr ^ 2
        If i = 2 Then BarsPerRow = 2
    Next i
    Iyr = Iyr - BarArea * MR * Yr ^ 2
    Yr = -ConcR
    BarsPerRow = 1
    LayerA(i, 1) = LayerA(i - 1, 2)
    LayerA(i, 2) = Sect(1, 1)
    LayerA(i, 3) = LayerA(i - 1, 3) - BarArea * BarsPerRow
    LayerA(i, 4) = 0
    LayerA(i, 5) = LayerA(i, 3) * (LayerA(i, 4) - Yr)
    LayerA(1, 6) = Iyr

    For i = 2 To Nlayers - 1
        Yr = ConcR - LayerA(i - 1, 2)
        LayerA(i, 6) = LayerA(i - 1, 6) - BarArea * BarsPerRow * (Yr - LayerA(i - 1, 4)) ^ 2 - LayerA(i, 3) * (LayerA(i, 4) - LayerA(i - 1, 4)) ^ 2
        If i = 2 Then BarsPerRow = 2
    Next i
    BarsPerRow = 1
    Yr = ConcR - LayerA(i - 1, 2)
    Ireo = LayerA(i - 1, 6) - BarArea * BarsPerRow * (Yr - LayerA(i - 1, 4)) ^ 2 - LayerA(i, 3) * (LayerA(i, 4) - LayerA(i - 1, 4)) ^ 2
    LayerA(i, 6) = Ireo
    CircReoLayers = 1
End Function

Function CircNALayer(Sect As Variant, Loads As Variant, LayerA() As Double) As Variant
    Dim NALAyer As Long, Momin As Double, Axin As Double, ConcR As Double, Ecc As Double, Nlayers As Long
    Dim Acomp As Double, Icomp As Double, fct As Double, SectData(1 To 6) As Double, QComp As Double, EccComp As Double
    Dim i As Long, NumReo As Double

    ' Find layer containing the Neutral axis
    If TypeName(Loads) = "Range" Then Loads = Loads.Value2
    Momin = Loads(2, 1) * 1000000
    Axin = Loads(1, 1) * 1000
    ConcR = Sect(1, 1) / 2
    NumReo = Sect(3, 1)
    Nlayers = (Int(NumReo / 2) + 2)

    If Axin <> 0 Then Ecc = Momin / Axin - ConcR Else Ecc = 1000000000#


    ' Check for section entirely in compression
    NALAyer = 1
    i = 0
    If Axin > 0 Then
        Acomp = Pi * ConcR ^ 2 + LayerA(Nlayers, 3)
        Icomp = Pi * ConcR ^ 4 / 4 + LayerA(Nlayers, 6)
        If (Axin / Acomp - Momin / (Icomp / ConcR)) > 0 Then
            NALAyer = Nlayers + 1
        End If
    End If

    ' Check for section entirely in tension
    If Axin < 0 Then
        Acomp = LayerA(1, 3)
        Icomp = LayerA(1, 6)
        fct = (Axin / Acomp + Momin / (Icomp / (ConcR - MinD)))
        If fct < 0 Then
            NALAyer = 0
        End If
    End If

    If NALAyer = 1 Then
        NALAyer = 0

        For i = 1 To Nlayers
            SectData(2) = ConcR
            SectData(3) = LayerA(i, 2)
            SectData(4) = LayerA(i, 3)
            SectData(5) = LayerA(i, 5)

            QComp = CalcQ(SectData, LayerA(i, 2))

            If NALAyer = 0 Then
                SectData(1) = ConcR
                SectData(2) = LayerA(i, 3)
                SectData(3) = LayerA(i, 4)
                SectData(4) = LayerA(i, 6)
                SectData(5) = Ecc
                SectData(6) = 1
                EccComp = CircleQxoI(SectData, LayerA(i, 2))

                If Axin < 0 Then
                    If (QComp < 0 And EccComp < 0) Or (QComp > 0) Then NALAyer = i
                Else
                    If EccComp > 0 Then NALAyer = i
                End If
                If NALAyer > 0 Then Exit For
            End If
        Next i
    End If


    If NALAyer = 0 Then NALAyer = i

    CircNALayer = NALAyer

End Function

Function CircNA0(ByRef SectData As Variant, NALAyer As Variant, LayerA As Variant) As Variant
    Dim B As Double
    Dim ConcR As Double, Ang As Double, Y0 As Variant
    Dim Xa(1 To 18, 1 To 1) As Variant, Y As Double
    Dim QNARnf As Double
    Dim YMin As Double, YMax As Double, NewY As Double
    Dim Areomax As Double, Qreomax As Double, YcNew As Double, Acnew As Double, QNew As Double
    Dim Iconcnew As Double, Inew As Double, SectData2(1 To 12) As Variant
    Dim i As Long


    ' Find depth of NA by iteration for 0 axial load
    i = NALAyer    ' (1, 1)
    ConcR = SectData(2)
    YMin = LayerA(i, 1)
    YMax = LayerA(i, 2)
    Areomax = LayerA(i, 3)
    Qreomax = LayerA(i, 5)
    SectData2(1) = 1
    SectData2(2) = ConcR
    SectData2(3) = LayerA(i, 2)
    SectData2(4) = Areomax
    SectData2(5) = Qreomax


    Y0 = QuadBrent("calcq", YMin, YMax, SectData2)

    NewY = Y0(1, 1)


    Y = NewY
    B = (ConcR ^ 2 - (ConcR - NewY) ^ 2) ^ 0.5
    Ang = WorksheetFunction.Atan2(ConcR - NewY, B)

    YcNew = (2 * ConcR / 3) * ((Sin(Ang) ^ 3) / (Ang - Sin(Ang) * Cos(Ang)))
    Acnew = ConcR ^ 2 * Ang - B * (ConcR - NewY)

    QNARnf = Qreomax - Areomax * (YMax - NewY)
    QNew = QNARnf + Acnew * (YcNew - (ConcR - NewY))
    Iconcnew = Acnew * (ConcR ^ 2 / 4 * (1 + (2 * (Sin(Ang)) ^ 3 * Cos(Ang)) / ((Ang - Sin(Ang) * Cos(Ang)))) - (YcNew) ^ 2 + (YcNew - (ConcR - NewY)) ^ 2)
    Inew = Iconcnew + LayerA(i, 6) + Areomax * (NewY - (ConcR - LayerA(i, 4))) ^ 2



    Xa(1, 1) = Y
    Xa(2, 1) = Iconcnew
    Xa(3, 1) = Inew - Iconcnew
    Xa(4, 1) = Acnew
    Xa(5, 1) = Areomax
    Xa(6, 1) = Acnew + Areomax
    Xa(7, 1) = QNew - QNARnf
    Xa(8, 1) = QNARnf


    CircNA0 = Xa

End Function


Function CalcQ(SectData As Variant, NewY As Double) As Double
    Dim ConcR As Double, B As Double, Ang As Double, YcNew As Double, Acnew As Double
    Dim Qreomax As Double, Areomax As Double, Yconcb As Double, CallFunc As Long

    CallFunc = SectData(1)
    ConcR = SectData(2)
    Yconcb = SectData(3)

    Areomax = SectData(4)
    Qreomax = SectData(5)


    B = (ConcR ^ 2 - (ConcR - NewY) ^ 2) ^ 0.5
    Ang = WorksheetFunction.Atan2(ConcR - NewY, B)
    YcNew = (2 * ConcR / 3) * ((Sin(Ang) ^ 3) / (Ang - Sin(Ang) * Cos(Ang)))
    Acnew = ConcR ^ 2 * Ang - B * (ConcR - NewY)

    CalcQ = Qreomax - Areomax * (Yconcb - NewY) + Acnew * (YcNew - (ConcR - NewY))

End Function



Function MoverZC(Sect As Variant, LayerA, Loads, NALAyer, StressA) As Variant
    Dim Dcent As Double, Acomp As Double, Icomp As Double, ZTop As Double, Zbot As Double, Xa(1 To 18, 1 To 1) As Variant
    Dim SigAx As Double, NettMomCent As Double, Axinps
    Dim DSect As Double, DNA As Double

    ' Find depth of NA for NA outside the concrete section
    DSect = Sect(1, 1)
    Dcent = DSect / 2
    If NALAyer = 0 Then

        Acomp = LayerA(1, 3)
        Icomp = LayerA(1, 6)
    Else
        NALAyer = NALAyer - 1
        Acomp = Pi * Dcent ^ 2 + LayerA(NALAyer, 3)
        Icomp = LayerA(NALAyer, 6) + Dcent ^ 4 * Pi / 4

    End If

    NettMomCent = Loads(2, 1) * 1000000#
    Axinps = Loads(1, 1) * 1000

    ZTop = Icomp / Dcent
    Zbot = Icomp / (DSect - Dcent)

    SigAx = Axinps / Acomp

    StressA(1, 1) = SigAx + NettMomCent / ZTop
    StressA(4, 1) = SigAx - NettMomCent / Zbot

    DNA = DSect * StressA(1, 1) / (StressA(1, 1) - StressA(4, 1))

    Xa(1, 1) = DNA
    If NALAyer = 0 Then
        Xa(2, 1) = 0
        Xa(3, 1) = Icomp
        Xa(4, 1) = 0
        Xa(5, 1) = Acomp
        Xa(6, 1) = Acomp
        Xa(7, 1) = Empty
        Xa(8, 1) = Acomp * (Dcent - DNA)
    Else
        Xa(3, 1) = LayerA(NALAyer, 6)
        Xa(2, 1) = Icomp - Xa(3, 1)
        Xa(6, 1) = Acomp
        Xa(5, 1) = LayerA(NALAyer, 3)
        Xa(4, 1) = Acomp - Xa(5, 1)
        Xa(8, 1) = Xa(5, 1) * (Dcent - DNA)
        Xa(7, 1) = Xa(4, 1) * (Dcent - DNA)
    End If
    MoverZC = Xa
End Function


Function CircleQxoI(SectData As Variant, X As Double) As Variant
    Dim R As Double, H As Double, Theta As Double, A As Double, Xcr As Double
    Dim Icc As Double, Iccent As Double, Icb As Double, Qcb As Double
    Dim Ast As Double, Istc As Double, Xsc As Double, Ecc As Double
    Dim Qsb As Double, Isb As Double, outA(1 To 8, 1 To 1), CallFunc As Long

    If TypeName(SectData) = "Range" Then SectData = SectData.Value2
    R = SectData(1)
    Ast = SectData(2)
    Xsc = SectData(3)
    Istc = SectData(4)
    Ecc = SectData(5)
    CallFunc = SectData(6)

    ' Concrete properties
    If X > 0 Then
        If X < 2 * R Then
            H = (R ^ 2 - (R - X) ^ 2) ^ 0.5
            Theta = WorksheetFunction.Atan2((R - X), H)
            A = R ^ 2 * (Theta - (Sin(2 * Theta) / 2))
            Xcr = (2 * R / 3) * ((Sin(Theta) ^ 3) / (Theta - Sin(Theta) * Cos(Theta)))
            Qcb = A * (X - (R - Xcr))
            Icc = A * R ^ 2 / 4 * (1 + (2 * (Sin(Theta)) ^ 3 * Cos(Theta)) / ((Theta - Sin(Theta) * Cos(Theta))))
            Iccent = Icc - A * Xcr ^ 2
        Else
            A = Pi * R ^ 2
            Qcb = A * (X - R)
            Iccent = A * R ^ 2 / 4
        End If
        Icb = Iccent + A * (Xcr - (R - X)) ^ 2

    Else
        Qcb = 0
        Icb = 0
    End If
    ' Reinforcement properties
    Qsb = Ast * (X - (R - Xsc))
    Isb = Istc + Ast * ((R - Xsc) - X) ^ 2

    If CallFunc = 1 Then
        CircleQxoI = ((Qcb + Qsb) * (Ecc + X) / (Icb + Isb)) - 1

    Else
        outA(1, 1) = X
        outA(2, 1) = Icb
        outA(3, 1) = Isb
        outA(4, 1) = A
        outA(5, 1) = Ast
        outA(6, 1) = A + Ast
        outA(7, 1) = Qcb
        outA(8, 1) = Qsb
        CircleQxoI = outA
    End If


End Function

Function CircCrack(Sect As Variant, Loads As Variant, Ireo As Double, StrainA As Variant, Out1 As Long, Out2 As Double, Ig As Double) As Variant
    Dim fct As Double, fc As Double, fct3600 As Double, fct_EC2 As Double, Es As Double, Epscs As Double, MR As Double, CMR As Double
    Dim Anett As Double, CArea As Double, CDepth As Double, ZConc As Double, Fcs As Double, Astot As Double
    Dim Pt As Double, Pc As Double, Depth As Double, Dcomp As Double, Diatens As Double, Dtens As Double
    Dim Axin As Double, Momin As Double, W As Double, CCrackA(1 To 9, 1 To 1) As Double
    Dim Reod As Double, ReoR As Double, BarArea As Double, NumReo As Double, ReoCov As Double
    Dim Mcr3600a As Double, Mcr3600b As Double, Mcr_EC2 As Double, McrBS5400 As Double, Tensdepth As Double
    Dim i As Long, Mq_Md As Double, Kbth As Double, Ec As Double
    Dim Strscomp As Double, Strstens As Double, K_1 As Double, K_2 As Double, Strctens As Double, Strc As Double, Aceff As Double, Astens As Double
    Dim Ppeff As Double, CSpace As Double, CSpaceMax As Double, FctEff As Double, K_t As Double, Sigstens As Double
    Dim Epscm As Double, CWidth As Double, Beta As Double, Zeta As Double, CrackRatio As Double
    Dim Epsstop As Double, Epssbot As Double, AsComp As Double, Sg As Double, Xcr As Double, Sbase As Double, Dcent As Double, Scr As Double
    Dim Curvesg As Double, Curvescr As Double, Curveseff As Double, Out2a As Double, X As Double, BarSpace As Double
    Dim Curve1 As Double, Curve1PS As Double, Icr As Double, Ief As Double, Zt As Double, Zb As Double

    If TypeName(Sect) = "Range" Then Sect = Sect.Value2
    If TypeName(Loads) = "Range" Then Loads = Loads.Value2
    If TypeName(StrainA) = "Range" Then StrainA = StrainA.Value2

    Axin = Loads(1, 1)
    Momin = Loads(2, 1)
    Depth = Sect(1, 1)
    CDepth = Depth / 2

    CArea = Pi * CDepth ^ 2
    MR = Sect(7, 1) / Sect(8, 1)
    CMR = MR - 1
    Reod = Sect(2, 1)
    ReoR = Reod / 2
    BarArea = ReoR ^ 2 * Pi
    NumReo = Sect(3, 1)
    ReoCov = Sect(4, 1)
    Astot = BarArea * NumReo
    fc = Sect(5, 1)
    Es = Sect(7, 1)
    Ec = Sect(8, 1)
    fct = Sect(9, 1)
    Epscs = Sect(10, 1)
    Dcomp = ReoCov + ReoR
    Dtens = Sect(1, 1) - Dcomp


    ' Cracking stress and moment

    If fct = -1 Then
        fct3600 = 0.6 * fc ^ 0.5
        If fc <= 50 Then
            fct_EC2 = 0.3 * fc ^ (2 / 3)
        Else
            fct_EC2 = 2.12 * Log(1 + fc / 10)
        End If
    Else
        fct3600 = fct
        fct_EC2 = fct
    End If

    Anett = CArea + CMR * (Astot)
    ' Ig = Iucomp + Pi * CDepth ^ 4 / 4
    ZConc = Ig / ((CDepth))
    Pt = Astot / (2 * CArea)
    Pc = Pt
    Fcs = (2.5 * Pt - 0.8 * Pc) / (1 + 50 * Pt) * Es * Epscs / 1000000#

    ' AS3600 cracking moment including shrinkage
    Mcr3600a = (fct3600 - Fcs + (Axin * 1000) / CArea) * ZConc / 1000000
    ' AS3600 cracking moment neglecting shrinkage
    Mcr3600b = (fct3600 + (Axin * 1000) / CArea) * ZConc / 1000000
    Mcr_EC2 = (fct_EC2 + (Axin * 1000) / CArea) * ZConc / 1000000  ' + (momin - momin)
    McrBS5400 = (1 + (Axin * 1000) / CArea) * ZConc / 1000000


    X = StrainA(1, 1)
    Strc = StrainA(2, 1)
    Strscomp = StrainA(3, 1)
    Strstens = StrainA(4, 1)
    Sigstens = Strstens * Es
    Strctens = StrainA(5, 1)
    Select Case Out1
    Case 1:
        CCrackA(1, 1) = fct3600
        CCrackA(2, 1) = Mcr3600a
        CCrackA(3, 1) = Mcr3600b
        CCrackA(4, 1) = fct_EC2
        CCrackA(5, 1) = Mcr_EC2
        CCrackA(6, 1) = McrBS5400


        ' Crack width to EC 2. Use narrow rectangular section of width equal to bar spacing
    Case 2:
        ' If Code = 3 Then
        If Abs(Momin) < Mcr_EC2 Then  ' And Out2 < 1 Then
            CCrackA(1, 1) = 0
        Else
            K_1 = 0.8
            If Strctens - Strc < Strctens Then    ' Strctens = strain at tens face; Strc = strain at comp face
                K_2 = 0.5
            Else
                K_2 = (Strctens + Strc) / (2 * Strctens)
            End If

            Aceff = (Depth - Dtens) * 2.5
            If Aceff > (Depth - X) / 3 Then Aceff = (Depth - X) / 3
            If Aceff > Depth / 2 Then Aceff = Depth / 2
            BarSpace = Pi * (Depth - (ReoCov + ReoR) * 2) / NumReo
            Aceff = Aceff * BarSpace
            Astens = BarArea
            AsComp = Astens
            Ppeff = Astens / Aceff

            CSpace = 3.4 * ReoCov + 0.425 * K_1 * K_2 * Reod / Ppeff
            CSpaceMax = 1.3 * (Depth - X)
            If CSpace > CSpaceMax Then CSpace = CSpaceMax
            FctEff = fct_EC2
            K_t = Out2 - Int(Out2)
            Epscm = (-Sigstens - (K_t * FctEff / Ppeff * (1 + MR * Ppeff))) / Es
            If Epscm < 0.6 * -Sigstens / Es Then Epscm = 0.6 * -Sigstens / Es
            CWidth = CSpace * Epscm

            ' Select Case Out2:
            'Case Is < 1:
            CCrackA(1, 1) = CWidth

            'Case Is < 2:
            CCrackA(2, 1) = CSpace
        End If

        ' Case Is < 3:
        CCrackA(3, 1) = (Strc - Strctens) / (Depth) * 1000

        Beta = Out2 - Int(Out2)
        If Out2 = 4 Then Beta = 1
        Zeta = 0

        If Abs(Momin) > Mcr_EC2 Then  ' Or Cracked = True Then
            CrackRatio = Mcr_EC2 / Momin
            If CrackRatio > 1 Then CrackRatio = 1
            Zeta = 1 - Beta * (CrackRatio) ^ 2
            Curve1 = CCrackA(3, 1)
            Curve1PS = (Strscomp - Strstens) / (Dtens - Dcomp) * 1000
            Icr = (Momin / 1000) / (Curve1 * Ec)

            Ief = Icr / (1 - Beta * (1 - Icr / (Ig / 1000000000000#)) * CrackRatio ^ 2)
        Else
            Zt = Ig / (CDepth - Dcomp)
            Zb = Ig / (CDepth - Dtens)

            Strscomp = (Axin * 1000 / Anett + (Momin * 1000000 + Axin * 1000 * (CDepth - Depth / 2)) / Zt) / Ec
            Strstens = (Axin * 1000 / Anett + (Momin * 1000000 + Axin * 1000 * (CDepth - Depth / 2)) / Zb) / Ec
            Curve1 = (Strscomp - Strstens) / (Dtens - Dcomp) * 1000
            CCrackA(3, 1) = Curve1
            If Epsstop <> 0 Or Epssbot <> 0 Then
                Strscomp = Strscomp - Epsstop
                Strstens = Strstens - Epssbot

            End If
            Curve1PS = (Strscomp - Strstens) / (Dtens - Dcomp) * 1000
            Ief = (Momin / 1000) / (Curve1 * Ec)
            Icr = Ief
        End If

        CCrackA(4, 1) = (Momin / 1000) / (Ief * Ec)

        Sg = (Astens * (Dtens - Depth / 2) - AsComp * (Depth / 2 - Dcomp)) / 1000000000#
        If Abs(Momin) > Mcr_EC2 Then
            Xcr = X
            If Xcr < 0 Then Xcr = 0
            ' Sbase = (Es / Ec) * (Astens * (Depth - Dtens) + AsComp * (Depth - Dcomp)) + W * Xcr * (Depth - Xcr / 2)
            Dcent = StrainA(6, 1)    ' Depth - Sbase / ((Astens + AsComp) * (Es / Ec) + W * Xcr)
            Scr = (Astens * (Dtens - Dcent) + AsComp * (Dcomp - Dcent)) / 1000000000#
        Else
            Scr = Sg
        End If

        Curvesg = Epscs / 1000000# * Es / Ec * Sg / Ig


        Curvescr = Epscs / 1000000# * Es / Ec * Scr / Icr
        Curveseff = Zeta * Curvescr + (1 - Zeta) * Curvesg
        CCrackA(5, 1) = Curveseff
        CCrackA(6, 1) = Curveseff + (Momin / 1000) / (Ief * Ec)


        '   End If
        If Out2 >= 1 Then
            If (Out2 - Int(Out2)) > 0 Then Out2a = Int(Out2) + 1 Else Out2a = Out2
            CCrackA(1, 1) = CCrackA(Out2a, 1)
        End If
    End Select



    CircCrack = CCrackA
End Function

