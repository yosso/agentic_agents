Attribute VB_Name = "mEstress"
Option Explicit
Enum DCode
    AS3600 = 1
    AS5100 = 2
    EC2 = 3
    BS5400 = 4
    BS8100 = 5
    CEB_FIP = 6
    AS3600_2009 = 7
    AS600_2009D = 8
End Enum


Private E_1 As Double, E_2 As Double, MR As Double, W As Double, Depth As Double, DNA0 As Double
Private Dtens As Double, Dcomp As Double, Astens As Double, AsComp As Double


Public Function Estress(ByVal Estressin As Variant, ByVal Axin As Variant, ByVal Momin As Variant, Out1 As Long, _
                        ByVal Out2 As Double, Optional ByVal PreStress As Variant, Optional ByVal Code As DCode, _
                        Optional ByVal DepthA As Variant, Optional ByVal Ect As Double, Optional Cracked As Boolean) As Variant
    Dim ecells As Variant, Estressa() As Variant, PStressA As Variant, PStress1 As Double, Epssbot As Double, Epsstop As Double
    Dim PSMoment As Double, PSTotal As Double, PSForce As Double, NettMom As Double, Nettax As Double, ax As Variant
    Dim Diabot As Double, Numbot As Double, Covbot As Double
    Dim Diatop As Double, Numtop As Double, Covtop As Double
    Dim CovTens As Double, NumTens As Double, Diatens As Double
    Dim Astop As Double, Asbot As Double, Dtop As Double, Dbot As Double
    Dim fc As Double, Fys As Double, Es As Double, Eys As Double, Ec As Double
    Dim X As Variant, SigC As Variant, Pc As Variant, Pgross As Variant
    Dim LAc As Double, LAstens As Double, LAscomp As Double
    Dim Mome As Variant, NMR As Double, srf As Double
    Dim Sigctens As Double, A1 As Double, A2 As Double, A3 As Double, Strc As Double, Strscomp As Double
    Dim Strstens As Double, Strctens As Double, Sigscomp As Double
    Dim Zeta As Double, Beta As Double, Ief As Double
    Dim Sigstens As Double, I_ As Double, Sg As Double, Scr As Double, Icr As Double
    Dim Curvesg As Double, Curvescr As Double, Curveseff As Double, Dcent As Double, Sbase As Double, Xcr As Double

    Dim A As Double, B As Double, C As Double, D As Double, numrealroots As Long, root1 As Double, root2 As Double, root3 As Double
    Dim Anett As Double, CDepth As Double, Iconc As Double, Zt As Double, Zb As Double, SigComp As Double, SigTens As Double
    Dim PScomp As Double, PStens As Double, PTot As Double, LAccomp As Double, LActens As Double, Mc As Double
    Dim Mscomp As Double, Mstens As Double, Mtot As Double
    Dim Maxcomp As Double, MaxTens As Double, Maxcompmom As Double, Maxtensmom As Double, EComp As Double, ETens As Double, EAct As Double
    Dim mSign As Long
    Dim K_1 As Double, K_2 As Double, Aceff As Double, Ppeff As Double, FctEff As Double, K_t As Double
    Dim CSpace As Double, CSpaceMax As Double, Epscm As Double, Mq_Md As Double, Kbth As Double, Tensdepth As Double
    Dim TensstrArea As Double, Str_m As Double, Str_m1 As Double, Str_m2 As Double, acr As Double
    Dim CWidth As Double
    Dim fct As Double, fct3600 As Double, Mcr3600a As Double, Mcr3600b As Double
    Dim fct_EC2 As Double, Mcr_EC2 As Double, ZConc As Double, McrBS5400 As Double
    Dim Ig As Double, MaxTens2 As Double, Epscs As Double, P As Double, Fcs As Double
    Dim Layer As Long, PcAdjComp As Double, PcAdjTens As Double, Curve1 As Double, Curve1PS As Double, CrackRatio As Double
    Dim i As Long, Out2a As Long

    Const Minax As Double = 0.1
    ecells = GetArray(Estressin)
    If IsMissing(PreStress) = False Then
        PStressA = GetArray(PreStress)
        PStress1 = PStressA(2, 1)
    End If
    If IsMissing(DepthA) = False Then
        DepthA = GetArray(DepthA)
        Depth = DepthA(1, 1)
    End If
    If Code = 0 Then Code = 1

    W = ecells(1, 1)
    If IsMissing(DepthA) = True Then Depth = ecells(2, 1)
    Diabot = ecells(6, 1)
    Numbot = ecells(7, 1)
    Covbot = ecells(8, 1)
    Diatop = ecells(3, 1)
    Numtop = ecells(4, 1)
    Covtop = ecells(5, 1)
    fc = ecells(9, 1)
    Fys = ecells(10, 1)
    Es = ecells(11, 1)
    If Ect = 0 Then Ec = ecells(12, 1) Else Ec = Ect
    fct = ecells(13, 1)
    Epscs = ecells(14, 1)

    Axin = GetArray(Axin)
    Momin = GetArray(Momin)

    ReDim Estressa(1 To UBound(Axin) - LBound(Axin) + 1, 1 To 11)

    For Each ax In Axin
        i = i + 1
        If IsMissing(DepthA) = False Then Depth = DepthA(i, 1)
        Mome = Momin(i, 1)

        Dbot = Depth - (Covbot + Diabot / 2)
        Dtop = Covtop + Diatop / 2

        Asbot = Numbot * (Diabot / 2) ^ 2 * Pi
        Astop = Numtop * (Diatop / 2) ^ 2 * Pi
        Eys = Fys / Es

        MR = Es / Ec
        NMR = Es / Ec - 1
        srf = 1 - Ec / Es
        Ig = Depth ^ 3 * W / (12 * 1000000000000#)

        X = 0
        Sigctens = 0

        ' Calculate Prestress force and prestress moment
        If IsMissing(PreStress) = False Then
            PSMoment = 0
            PSTotal = 0

            If PStressA(1, 1) <> 0 Then
                Epsstop = PStressA(1, 1) / Es
                PSForce = PStressA(1, 1) * Astop / 1000
                PSMoment = PSForce * (Depth / 2 - Dtop) / 1000   ' Moment about conc centroid
                PSTotal = PSForce
            End If
            If PStressA(2, 1) <> 0 Then
                Epssbot = PStressA(2, 1) / Es
                PSForce = PStressA(2, 1) * Asbot / 1000
                PSMoment = PSMoment + PSForce * (Depth / 2 - Dbot) / 1000     ' Moment about conc centroid
                PSTotal = PSTotal + PSForce
            End If
        End If
        ' Calculate nett moment, axial force and eccentricity
        NettMom = (Mome + PSMoment)
        If Abs(NettMom) = 0 Then NettMom = 0.000001
        Nettax = Round(ax + PSTotal, 6)

        ' Check for zero load
        If NettMom = 0 And Nettax = 0 Then
            SigC = 0
            Strc = 0
            Strscomp = 0
            Strstens = 0
            Strctens = 0
            GoTo ZeroLoad
        End If


        '   Max compressive and tensile force and moment

        Maxcomp = ((W * Depth) * fc + (Asbot + Astop) * fc * NMR) / 1000
        Maxcompmom = (Astop * (Depth / 2 - Dtop) + Asbot * (Depth / 2 - Dbot)) * fc * NMR / 1000000
        EComp = (Maxcompmom / Maxcomp)

        MaxTens = -(Asbot + Astop) * Fys / 1000
        Maxtensmom = -(Astop * (Depth / 2 - Dtop) + Asbot * (Depth / 2 - Dbot)) * Fys / 1000000
        ETens = Maxtensmom / MaxTens

        mSign = 1


        If Nettax <> 0 Then
            EAct = NettMom / Nettax

            If Nettax < 0 Then
                If EAct < ETens Then
                    mSign = 1
                Else
                    mSign = -1
                End If
            Else
                If EAct > EComp Then
                    mSign = 1
                Else
                    mSign = -1
                End If
            End If
        End If

        If Nettax = 0 And NettMom <> 0 Then mSign = NettMom / Abs(NettMom)

        If mSign = 1 Then
            Dcomp = Dtop
            Dtens = Dbot

            AsComp = Astop
            Astens = Asbot


            CovTens = Covbot
            NumTens = Numbot
            Diatens = Diabot
        End If

        If mSign = -1 Then
            Dcomp = Depth - Dbot
            Dtens = Depth - Dtop

            AsComp = Asbot
            Astens = Astop

            CovTens = Covtop
            NumTens = Numtop
            Diatens = Diatop
        End If

        NettMom = NettMom * mSign
        If Nettax <> 0 Then
            E_1 = NettMom * 1000 / Nettax
            E_2 = E_1 - Depth / 2
        End If

        'Depth of NA for 0 axial load
        A = W / 2
        B = AsComp * NMR + Astens * MR
        C = -(AsComp * NMR * Dcomp + Astens * MR * Dtens)
        DNA0 = Quadratic(A, B, C, 2)
        If DNA0 < Dcomp Then
            B = (AsComp + Astens) * MR
            C = -(AsComp * Dcomp + Astens * Dtens) * MR
            DNA0 = Quadratic(A, B, C, 2)
        End If

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

        Anett = Depth * W + NMR * (Astens + AsComp)
        CDepth = (NMR * (Astens * Dtens + AsComp * Dcomp) + W * Depth ^ 2 / 2) / Anett
        Ig = (NMR * (Astens * (CDepth - Dtens) ^ 2 + AsComp * (CDepth - Dcomp) ^ 2) + W * (Depth ^ 3 / 12 + Depth * (CDepth - Depth / 2) ^ 2))
        ZConc = Ig / ((Depth - CDepth) * 1000000000#)
        P = Astens / (W * (Depth - CovTens - Diatens / 2))
        Fcs = (1.5 * P / (1 + 50 * P)) * Es * Epscs / 1000000#

        ' AS3600 cracking moment including shrinkage
        Mcr3600a = (fct3600 - Fcs + (Nettax * 1000) / (Depth * W)) * ZConc * 1000
        ' AS3600 cracking moment neglecting shrinkage
        Mcr3600b = (fct3600 + (Nettax * 1000) / (Depth * W)) * ZConc * 1000
        Mcr_EC2 = (fct_EC2 + (Nettax * 1000) / (Depth * W)) * ZConc * 1000    ' + (NettMom - Mome)
        McrBS5400 = (1 + (Nettax * 1000) / (Depth * W)) * ZConc * 1000

        If Abs(NettMom) <= Mcr_EC2 Then
            Estressa(1, 1) = "Uncracked"
            Estressa(1, 2) = Ig
            Estress = Estressa
            Exit Function
        End If

        If Nettax = 0 Then
            X = DNA0

            If X < Dcomp Then
                I_ = (AsComp * (X - Dcomp) ^ 2 + Astens * (X - Dtens) ^ 2) * MR + W * X ^ 3 / 3
            Else
                I_ = (AsComp * srf * (X - Dcomp) ^ 2 + Astens * (X - Dtens) ^ 2) * MR + W * X ^ 3 / 3
            End If

        Else
            If Abs(Nettax) < Minax Then
                Nettax = Minax
                E_1 = NettMom * 1000 / Nettax
                E_2 = E_1 - Depth / 2
            End If

            A1 = Astens * (Depth / 2 - Dtens)
            A2 = AsComp * (Depth / 2 - Dcomp)
            A3 = W / 2 * (Ec / Es)

            Layer = NALAyer(Nettax)

            Select Case Layer
            Case 1
                '   x < 0

                A = 0
                B = 0
                C = A1 + A2 - E_1 * (AsComp + Astens)
                D = (E_1 * (AsComp * Dcomp + Astens * Dtens) - (A1 * Dtens + A2 * Dcomp))

                X = -D / C

                I_ = (AsComp * (X - Dcomp) ^ 2 + Astens * (X - Dtens) ^ 2) * MR


            Case 2
                '   x < dcomp

                A = -A3 / 3
                B = (A3 * (Depth / 2 - E_1))
                C = A1 + A2 - E_1 * (AsComp + Astens)
                D = (E_1 * (AsComp * Dcomp + Astens * Dtens) - (A1 * Dtens + A2 * Dcomp))

                cubicsub A, B, C, D, numrealroots, root1, root2, root3

                If root1 > 0 And root1 < Dcomp Then X = root1
                If root2 > 0 And root2 < Dcomp Then X = root2
                If root3 > 0 And root3 < Dcomp Then X = root3

                I_ = (AsComp * (X - Dcomp) ^ 2 + Astens * (X - Dtens) ^ 2) * MR + W * X ^ 3 / 3

            Case 3
                '   dcomp < x < dtens

                A2 = AsComp * (Depth / 2 - Dcomp) * srf

                A = -A3 / 3
                B = (A3 * (Depth / 2 - E_1))
                C = A1 + A2 - E_1 * (AsComp * srf + Astens)
                D = (E_1 * (AsComp * srf * Dcomp + Astens * Dtens) - (A1 * Dtens + A2 * Dcomp))

                cubicsub A, B, C, D, numrealroots, root1, root2, root3

                If root1 > Dcomp And root1 < Dtens Then X = root1 Else
                If root2 > Dcomp And root2 < Dtens Then X = root2 Else
                If root3 > Dcomp And root3 < Dtens Then X = root3 Else

                I_ = (AsComp * (X - Dcomp) ^ 2 * srf + Astens * (X - Dtens) ^ 2) * MR + W * X ^ 3 / 3
            Case 4
                '   dtens < x < depth

                A1 = A1 * srf
                A2 = A2 * srf

                A = -A3 / 3
                B = (A3 * (Depth / 2 - E_1))
                C = A1 + A2 - E_1 * (AsComp + Astens) * srf
                D = (E_1 * srf * (AsComp * Dcomp + Astens * Dtens) - (A1 * Dtens + A2 * Dcomp))

                cubicsub A, B, C, D, numrealroots, root1, root2, root3

                If root1 > Dtens And root1 < Depth Then X = root1 Else
                If root2 > Dtens And root2 < Depth Then X = root2 Else
                If root3 > Dtens And root3 < Depth Then X = root3 Else

                I_ = (AsComp * (X - Dcomp) ^ 2 + Astens * (X - Dtens) ^ 2) * NMR + W * X ^ 3 / 3

            Case 5
                '    x > depth
                ' If nettax < 0 Then W = 0
                Anett = Depth * W + NMR * (Astens + AsComp)
                CDepth = (NMR * (Astens * Dtens + AsComp * Dcomp) + W * Depth ^ 2 / 2) / Anett
                Iconc = NMR * (Astens * (CDepth - Dtens) ^ 2 + AsComp * (CDepth - Dcomp) ^ 2) + W * (Depth ^ 3 / 12 + Depth * (CDepth - Depth / 2) ^ 2)
                Zt = Iconc / CDepth
                Zb = Iconc / (CDepth - Depth)

                SigComp = Nettax * 1000 / Anett + (NettMom * 1000000 + Nettax * 1000 * (CDepth - Depth / 2)) / Zt
                SigTens = Nettax * 1000 / Anett + (NettMom * 1000000 + Nettax * 1000 * (CDepth - Depth / 2)) / Zb

                X = Abs(Depth * SigComp / (SigComp - SigTens))
                I_ = (AsComp * (X - Dcomp) ^ 2 + Astens * (X - Dtens) ^ 2) * NMR + W * (Depth ^ 3 / 12 + (X - Depth / 2) ^ 2 * Depth)

            End Select

            ' Interpolate X for 0 < abs(nettax) < minax
            If Abs(Nettax) < Minax Then
                Nettax = Axin(i, 1)
                X = DNA0 + (X - DNA0) * Nettax / Minax
                If X < Dcomp Then
                    I_ = (AsComp * (X - Dcomp) ^ 2 + Astens * (X - Dtens) ^ 2) * MR + W * X ^ 3 / 3
                Else
                    I_ = (AsComp * srf * (X - Dcomp) ^ 2 + Astens * (X - Dtens) ^ 2) * MR + W * X ^ 3 / 3
                End If
            End If
        End If
printres:

        ' Concrete stress at compression face

        SigC = (NettMom * 1000000# + Nettax * 1000 * (X - Depth / 2)) * X / I_

        ' strains
        Strc = SigC / Ec
        Strscomp = Strc * (1 - Dcomp / X)
        Strstens = Strc * (1 - Dtens / X)
        Strctens = Strc * (1 - Depth / X)
        If Epssbot <> 0 Or Epsstop <> 0 Then
            If mSign = 1 Then
                Strscomp = Strscomp - Epsstop
                Strstens = Strstens - Epssbot
            Else
                Strscomp = Strscomp - Epssbot
                Strstens = Strstens - Epsstop
            End If
        End If

        ' other stresses
ZeroLoad:
        Sigscomp = Strscomp * Es
        ' If DComp < X Then Sigscomp = Sigscomp * srf
        Sigstens = Strstens * Es
        ' If DTens < X Then Sigstens = Sigstens * srf
        Sigctens = Strctens * Ec
        If Sigctens < 0 Then Sigctens = 0

        '   Forces

        PScomp = Sigscomp * AsComp / 1000
        PStens = Sigstens * Astens / 1000
        Pgross = 0
        If X > 0 Then Pgross = SigC / 2 * W * X / 1000
        If Sigctens > 0 Then Pgross = (SigC + Sigctens) / 2 * W * Depth / 1000
        If Dcomp < X Then
            PcAdjComp = AsComp * (Strc * (1 - Dcomp / X)) * Ec / 1000
            Pc = Pgross - PcAdjComp
            If Dtens < X Then
                PcAdjTens = Astens * (Strc * (1 - Dtens / X)) * Ec / 1000
                Pc = Pc - PcAdjTens
            End If
        Else
            Pc = Pgross
        End If
        PTot = Pc + PScomp + PStens

        ' Moments
        LAc = -X / 3 + Depth / 2
        LAccomp = Depth / 6
        LActens = -Depth / 6
        LAstens = -Dtens + Depth / 2
        LAscomp = -Dcomp + Depth / 2

        Mscomp = PScomp * LAscomp / 1000
        Mstens = PStens * LAstens / 1000

        Mc = Pgross * LAc / 1000
        If Sigctens > 0 Then Mc = W / 1000 * Depth / 2 * (SigC * LAccomp + Sigctens * LActens) / 1000
        If Dcomp < X Then
            Mc = Mc - PcAdjComp * LAscomp / 1000
            If Dtens < X Then Mc = Mc - PcAdjTens * LAstens / 1000
        End If

        Mtot = Mc + Mscomp + Mstens
        LAc = 0
        If Pc > 0 Then LAc = (Mc / Pc) * 1000


        Select Case Out1
        Case 1:
            If mSign = 1 Then Estressa(i, 1) = SigC Else Estressa(i, 1) = Sigctens
            If mSign = 1 Then Estressa(i, 2) = Sigscomp Else Estressa(i, 2) = Sigstens
            If mSign = 1 Then Estressa(i, 3) = Sigstens Else Estressa(i, 3) = Sigscomp
            If mSign = 1 Then Estressa(i, 4) = Sigctens Else Estressa(i, 4) = SigC
            If Out2 > 0 And Out2 < 5 Then Estressa(i, 1) = Estressa(i, Out2)

            Select Case Out2
            Case 0 To 4:
            Case 5:
                If Code = 1 Or Code = 2 Then
                    If Diatens >= 20 Or Depth > 300 Or Code = 2 Then
                        MaxTens = 760 - 173 * Log(Diatens)
                    Else
                        MaxTens = 580 - 114 * Log(Diatens)
                    End If
                    MaxTens2 = 400 - 0.8 * (W / NumTens)
                    If MaxTens2 > MaxTens Then MaxTens = MaxTens2
                    Estressa(i, 1) = MaxTens
                Else
                    Estressa(i, 1) = CVErr(xlErrNA)
                End If

            Case 6:
                If Code = 2 Then
                    MaxTens = 575 - 130 * Log(Diatens)
                    MaxTens2 = 320 - 0.8 * (W / NumTens)
                    If MaxTens2 > MaxTens Then MaxTens = MaxTens2
                    Estressa(i, 1) = MaxTens
                Else
                    Estressa(i, 1) = CVErr(xlErrNA)
                End If

            Case Else: Estressa(i, 1) = CVErr(xlErrNA)
            End Select


        Case 2:
            If mSign = 1 Then Estressa(i, 1) = Strc Else Estressa(i, 1) = Strctens
            If mSign = 1 Then Estressa(i, 2) = Strscomp Else Estressa(i, 2) = Strstens
            If mSign = 1 Then Estressa(i, 3) = Strstens Else Estressa(i, 3) = Strscomp
            If mSign = 1 Then Estressa(i, 4) = Strctens Else Estressa(i, 4) = Strc
            Estressa(i, 5) = (Strc - Strctens) / (Depth) * mSign * 1000

            If Out2 > 0 And Out2 < 6 Then Estressa(i, 1) = Estressa(i, Out2)

        Case 3: Select Case Out2
            Case 1: Estressa(i, 1) = Pc
            Case 2: If mSign = 1 Then Estressa(i, 1) = PScomp Else Estressa(i, 1) = PStens
            Case 3: If mSign = 1 Then Estressa(i, 1) = PStens Else Estressa(i, 1) = PScomp
            Case 4: Estressa(i, 1) = PTot
            Case Else: Estressa(i, 1) = CVErr(xlErrNA)
            End Select

        Case 4: Select Case Out2
            Case 1: Estressa(i, 1) = Mc * mSign
            Case 2: If mSign = 1 Then Estressa(i, 1) = Mscomp Else Estressa(i, 1) = -Mstens
            Case 3: If mSign = 1 Then Estressa(i, 1) = Mstens Else Estressa(i, 1) = -Mscomp
            Case 4: Estressa(i, 1) = Mtot * mSign
            Case Else: Estressa(i, 1) = CVErr(xlErrNA)
            End Select

        Case 5:
            Select Case Out2
            Case 1: Estressa(i, 1) = X
            Case 2: Estressa(i, 1) = LAc
            Case 3: Estressa(i, 1) = mSign
            Case 4: Estressa(i, 1) = fct3600
            Case 5: Estressa(i, 1) = Mcr3600a
            Case 6: Estressa(i, 1) = Mcr3600b
            Case 7: Estressa(i, 1) = fct_EC2
            Case 8: Estressa(i, 1) = Mcr_EC2
            Case 9: Estressa(i, 1) = McrBS5400
            Case Else: Estressa(i, 1) = CVErr(xlErrNA)
            End Select

        Case 6: Select Case Out2
            Case 1: Estressa(i, 1) = W
            Case 2: Estressa(i, 1) = Depth
            Case 3: Estressa(i, 1) = Diabot
            Case 4: Estressa(i, 1) = Numbot
            Case 5: Estressa(i, 1) = Covbot
            Case 6: Estressa(i, 1) = Diatop
            Case 7: Estressa(i, 1) = Numtop
            Case 8: Estressa(i, 1) = Covtop
            Case 9: Estressa(i, 1) = fc
            Case 10: Estressa(i, 1) = Fys
            Case 11: Estressa(i, 1) = Es
            Case 12: Estressa(i, 1) = Ec
            Case 13: Estressa(i, 1) = Nettax
            Case 14: Estressa(i, 1) = NettMom
            Case Else: Estressa(i, 1) = CVErr(xlErrNA)

            End Select

        Case 7: Select Case Out2
            Case 1: Estressa(i, 1) = AsComp
            Case 2: Estressa(i, 1) = Astens
            Case 3: Estressa(i, 1) = Dcomp
            Case 4: Estressa(i, 1) = Dtens
            Case 5: Estressa(i, 1) = Maxcomp
            Case 6: Estressa(i, 1) = Maxcompmom
            Case 7: Estressa(i, 1) = MaxTens
            Case 8: Estressa(i, 1) = Maxtensmom
            Case 9: Estressa(i, 1) = mSign
            Case 10: Estressa(i, 1) = Ig / 1000000000000#
            Case Else: Estressa(i, 1) = CVErr(xlErrNA)


            End Select

        Case 8:
            If Code = 4 Or Code = 5 Then
                If NettMom < Mcr3600b Then
                    Estressa(i, 1) = 0
                Else
                    Mq_Md = Out2
                    Kbth = 3.8 * Depth * W
                    Tensdepth = Depth - X
                    If Tensdepth <= 0 Then
                        Estressa(i, 1) = 0
                    Else
                        TensstrArea = -Strstens * Astens
                        If TensstrArea = 0 Then
                            Str_m = -Strctens
                        Else
                            Str_m1 = -Strctens - ((Kbth) / (TensstrArea) * (1 - Mq_Md) * 0.000000001)

                            Str_m2 = -Strctens
                            If Str_m1 < Str_m2 Then Str_m = Str_m1 Else Str_m = Str_m2
                        End If

                        acr = ((CovTens + Diatens / 2) ^ 2 + (W / NumTens / 2) ^ 2) ^ 0.5 - Diatens / 2

                        Estressa(i, 1) = (3 * acr * Str_m / (1 + 2 * (acr - CovTens) / (Tensdepth)))

                    End If
                    If Estressa(i, 1) < 0 Then Estressa(i, 1) = 0
                End If

            ElseIf Code = 3 Then
                If Abs(NettMom) < Mcr_EC2 Then  ' And Out2 < 1 Then
                    Estressa(i, 1) = 0
                Else
                    K_1 = 0.8
                    If Strctens - Strc < Strctens Then
                        K_2 = 0.5
                    Else
                        K_2 = (Strctens + Strc) / (2 * Strctens)
                    End If

                    Aceff = (Depth - Dtens) * 2.5
                    If Aceff > (Depth - X) / 3 Then Aceff = (Depth - X) / 3
                    Aceff = Aceff * W

                    Ppeff = Astens / Aceff

                    CSpace = 3.4 * (Depth - Dtens - Diatens / 2) + 0.425 * K_1 * K_2 * Diatens / Ppeff
                    CSpaceMax = 1.3 * (Depth - X)
                    If CSpace > CSpaceMax Then CSpace = CSpaceMax
                    FctEff = fct_EC2
                    K_t = Out2 - Int(Out2)
                    Epscm = (-Sigstens - (K_t * FctEff / Ppeff * (1 + MR * Ppeff))) / Es
                    If Epscm < 0.6 * -Sigstens / Es Then Epscm = 0.6 * -Sigstens / Es
                    CWidth = CSpace * Epscm

                    ' Select Case Out2:
                    'Case Is < 1:
                    Estressa(i, 1) = CWidth

                    'Case Is < 2:
                    Estressa(i, 2) = CSpace
                End If

                ' Case Is < 3:
                Estressa(i, 3) = (Strc - Strctens) / (Depth) * mSign * 1000

                Beta = Out2 - Int(Out2)
                If Out2 = 4 Then Beta = 1
                Zeta = 0

                If Abs(NettMom) > Mcr_EC2 Or Cracked = True Then
                    CrackRatio = Mcr_EC2 / NettMom
                    If CrackRatio > 1 Then CrackRatio = 1
                    Zeta = 1 - Beta * (CrackRatio) ^ 2
                    Curve1 = Estressa(i, 3)
                    Curve1PS = (Strscomp - Strstens) / (Dtens - Dcomp) * mSign * 1000
                    Icr = (Mome / 1000) / (Curve1 * Ec)

                    Ief = Icr / (1 - Beta * (1 - Icr / (Ig / 1000000000000#)) * CrackRatio ^ 2)
                Else
                    Zt = Ig / (CDepth - Dcomp)
                    Zb = Ig / (CDepth - Dtens)

                    Strscomp = (Nettax * 1000 / Anett + (NettMom * 1000000 + Nettax * 1000 * (CDepth - Depth / 2)) / Zt) / Ec
                    Strstens = (Nettax * 1000 / Anett + (NettMom * 1000000 + Nettax * 1000 * (CDepth - Depth / 2)) / Zb) / Ec
                    Curve1 = (Strscomp - Strstens) / (Dtens - Dcomp) * mSign * 1000
                    Estressa(i, 7) = Curve1
                    If Epsstop <> 0 Or Epssbot <> 0 Then
                        If mSign = 1 Then
                            Strscomp = Strscomp - Epsstop
                            Strstens = Strstens - Epssbot
                        Else
                            Strscomp = Strscomp - Epssbot
                            Strstens = Strstens - Epsstop
                        End If
                    End If
                    Curve1PS = (Strscomp - Strstens) / (Dtens - Dcomp) * mSign * 1000
                    Ief = (Mome / 1000) / (Curve1 * Ec)
                    Icr = Ief
                End If

                Estressa(i, 4) = (Mome / 1000) / (Ief * Ec)

                Sg = (Astens * (Dtens - Depth / 2) - AsComp * (Depth / 2 - Dcomp)) / 1000000000#
                If Abs(NettMom) > Mcr_EC2 Then
                    Xcr = X
                    If Xcr < 0 Then Xcr = 0
                    Sbase = (Es / Ec) * (Astens * (Depth - Dtens) + AsComp * (Depth - Dcomp)) + W * Xcr * (Depth - Xcr / 2)
                    Dcent = Depth - Sbase / ((Astens + AsComp) * (Es / Ec) + W * Xcr)
                    Scr = (Astens * (Dtens - Dcent) + AsComp * (Dcomp - Dcent)) / 1000000000#
                Else
                    Scr = Sg
                End If

                Curvesg = Epscs / 1000000# * Es / Ec * Sg / Ig


                Curvescr = Epscs / 1000000# * Es / Ec * Scr / Icr
                Curveseff = Zeta * Curvescr + (1 - Zeta) * Curvesg
                Estressa(i, 5) = Curveseff
                Estressa(i, 6) = Curveseff + (Mome / 1000) / (Ief * Ec)

                Estressa(i, 8) = Curve1PS
                If Estressa(i, 7) = 0 Then
                    Estressa(i, 9) = Estressa(i, 6) + Curve1PS - Estressa(i, 3)
                Else
                    Estressa(i, 9) = Estressa(i, 6) + Curve1PS - Estressa(i, 7)
                End If

            End If
            If Out2 >= 1 Then
                If (Out2 - Int(Out2)) > 0 Then Out2a = Int(Out2) + 1 Else Out2a = Out2
                Estressa(i, 1) = Estressa(i, Out2a)
            End If

        Case 9:
            Estressa(1, 1) = Strc
            Estressa(1, 2) = PTot
            Estressa(1, 3) = Mtot
            If Abs(Momin(i, 1)) > Mcr_EC2 Or Cracked = True Then
                If mSign = 1 Then Estressa(1, 4) = X Else Estressa(1, 4) = Depth - X
            Else
                Estressa(1, 4) = CDepth
            End If
            Estressa(1, 5) = fct_EC2
            Estressa(1, 6) = mSign
            Estressa(1, 7) = Ig
            Estressa(1, 8) = (Strc - Strctens) / (Depth) * mSign * 1000
            Estressa(1, 9) = Strctens
            Estressa(1, 10) = Mcr_EC2
            If mSign = 1 Then Estressa(1, 11) = X Else Estressa(1, 4) = Depth - X

        Case Else: Estressa(i, 1) = CVErr(xlErrNA)
        End Select


        GoTo Endfunc

dataerr:
        Estressa(i, 1) = CVErr(xlErrValue)
Endfunc:


    Next ax

    Estress = Estressa

End Function


Private Function NALAyer(ax) As Long
    Dim Q_ As Double, I_ As Double, EccL As Double


    ' NA on top face

    If ax < 0 Then
        Q_ = AsComp * -Dcomp + Astens * -Dtens
        I_ = AsComp * Dcomp ^ 2 + Astens * Dtens ^ 2
        EccL = I_ / Q_
        If E_2 >= EccL Then
            NALAyer = 1
            Exit Function
        End If
    End If


    ' NA at top steel
    Q_ = Astens * (Dcomp - Dtens) * MR + W * Dcomp ^ 2 / 2
    I_ = Astens * (Dcomp - Dtens) ^ 2 * MR + W * Dcomp ^ 3 / 3
    EccL = I_ / Q_ - Dcomp
    If ax > 0 Then
        If (Dcomp > DNA0 And E_2 >= EccL) Or (Dcomp < DNA0 And E_2 <= EccL) Then
            NALAyer = 2

            Exit Function
        End If
    Else
        If (Dcomp > DNA0 And E_2 <= EccL) Or (Dcomp < DNA0 And E_2 >= EccL) Then
            NALAyer = 2
            Exit Function
        End If
    End If

    ' NA at bottom steel
    Q_ = AsComp * (Dtens - Dcomp) * (MR - 1) + W * Dtens ^ 2 / 2
    I_ = AsComp * (Dtens - Dcomp) ^ 2 * (MR - 1) + W * Dtens ^ 3 / 3
    EccL = I_ / Q_ - Dtens
    If ax > 0 Then
        If E_2 >= EccL Then
            NALAyer = 3
            Exit Function
        End If
    Else
        If E_2 <= EccL Then
            NALAyer = 3
            Exit Function
        End If
    End If

    ' NA at bottom face
    Q_ = (AsComp * (Depth - Dcomp) + Astens * (Depth - Dtens)) * (MR - 1) + W * Depth ^ 2 / 2
    I_ = (AsComp * (Depth - Dcomp) ^ 2 + Astens * (Depth - Dtens) ^ 2) * (MR - 1) + W * Depth ^ 3 / 3
    EccL = I_ / Q_ - Depth
    If E_2 >= EccL Then
        NALAyer = 4
        Exit Function
    End If

    NALAyer = 5

End Function

