Attribute VB_Name = "mLPile"
Option Explicit
Option Base 1
Enum KOpt
    COM624 = 1
    kDiam = 2
End Enum




Function LatPile(Segments As Variant, Loads As Variant, SoilTabs As Variant, PileSect As Variant, _
                 Optional PYCurveA As Variant, Optional DefaultA As Variant, Optional Out As Long = 1, Optional KOption As KOpt = COM624) As Variant

' Koption = 1: initial stiffness (P/Y) for soil type 2 and 3 = Ki * Diam
' Koption = 2: initial stiffness (P/Y) for soil type 2 and 3 = Ki * Depth

    Dim NumPileSect As Long, PileSect2(1 To 14, 1 To 1) As Double
    Dim YA() As Variant, Depth As Double, LoadA() As Double, AxGrad As Double
    Dim AxLoad As Double, mom As Double, Beta As Double
    Dim MomA() As Double, k As Double
    Dim EIG As Double
    Dim NumNodes As Long, NumLNodes As Long
    Dim NumDivs As Long, SegLength As Double, i As Long, j As Long, n As Long, NumPYPoints As Long, NewEI As Double
    Dim PYA As Variant, Curve As Variant
    Dim LinLimits() As Double
    Dim SegRows As Long, TotDivs As Long, Sect As Long, SResA() As Double, YSum As Double, YDiff As Double, YNorm As Double
    Dim StiffDiff As Double, StiffSum As Double, StiffNorm As Double, PStiffDiff As Double, PStiffSum As Double, PStiffNorm As Double, NewStiff As Double
    Dim YTol As Double, StiffTol, PStiffTol As Double, MaxIts As Long

    If IsMissing(DefaultA) = False Then
        If TypeName(DefaultA) = "Range" Then DefaultA = DefaultA.Value2
        Beta = 5 + DefaultA(1, 1)
        MaxIts = DefaultA(2, 1)
        YTol = DefaultA(3, 1)
        StiffTol = DefaultA(4, 1)
        PStiffTol = DefaultA(5, 1)
    End If

    If Beta = 0 Then Beta = 5.5
    If MaxIts = 0 Then MaxIts = 20
    If YTol = 0 Then YTol = 0.001
    If StiffTol = 0 Then StiffTol = 0.001
    If PStiffTol = 0 Then PStiffTol = 0.001


    If TypeName(Segments) = "Range" Then Segments = Segments.Value2
    If TypeName(Loads) = "Range" Then Loads = Loads.Value2
    If TypeName(SoilTabs) = "Range" Then SoilTabs = SoilTabs.Value2
    If TypeName(PileSect) = "Range" Then PileSect = PileSect.Value2
    If TypeName(PYCurveA) = "Range" Then PYCurveA = PYCurveA.Value2

    SegRows = UBound(Segments)
    For i = 1 To SegRows
        TotDivs = TotDivs + Segments(i, 2)
    Next i
    NumNodes = TotDivs + 1
    ReDim FSA(1 To NumNodes, 1 To 3)
    ReDim YA(1 To NumNodes, 1 To 3)    ' input to PY624 function: Depth, Diam, Y
    ReDim SResA(1 To NumNodes, 1 To 6)
    ReDim LoadA(1 To 3, 1 To NumNodes)
    LoadA(1, 1) = 1
    LoadA(2, 1) = Loads(1, 1)
    LoadA(3, 1) = Loads(2, 1)

    NumPileSect = UBound(PileSect, 2)

    ReDim MomA(1 To NumNodes)
    ReDim CurveA(1 To NumNodes)

    n = 0
    FSA(1, 1) = 0
    YA(1, 1) = 0
    YA(1, 2) = PileSect(2, 1)
    k = 1
    For i = 1 To SegRows
        NumDivs = Segments(i, 2)
        SegLength = Segments(i, 1) / NumDivs
        If i > 1 Then Segments(i, 1) = Segments(i, 1) + Segments(i - 1, 1)
        For j = 1 To NumDivs
            n = n + 1
            FSA(n + 1, 1) = FSA(n, 1) + SegLength
            If FSA(n + 1, 1) > (PileSect(1, k) + 0.000001) Then k = k + 1
            YA(n + 1, 1) = FSA(n + 1, 1)
            YA(n + 1, 2) = PileSect(2, k)
        Next j
    Next i
    If Loads(5, 1) <= 0 Or Loads(5, 1) >= FSA(NumNodes, 1) Then
        AxGrad = (Loads(4, 1) - Loads(3, 1)) / FSA(NumNodes, 1)
    Else
        AxGrad = -Loads(3, 1) / Loads(5, 1)
    End If

    ReDim LinLimits(1 To (NumNodes), 1 To 4)
    n = 1
    Sect = 1
    For j = 1 To NumNodes
        Depth = FSA(j, 1)
        If Depth > (PileSect(1, Sect) + 0.000001) Then Sect = Sect + 1

        If TypeName(PileSect(3, Sect)) = "Double" Then
            FSA(j, 2) = PileSect(3, Sect)
        ElseIf UCase(PileSect(3, Sect)) = "C" Then
            EIG = PileSect(10, Sect) * Pi / 4 * (PileSect(2, Sect) / 2) ^ 4
            FSA(j, 2) = EIG
        ElseIf UCase(PileSect(3, Sect)) = "R" Then
            EIG = PileSect(10, Sect) / 12# * (PileSect(2, Sect) * (PileSect(13, Sect)) ^ 3)    '+ PileSect(4, Sect) ^ 2 * Pi / 4 * (PileSect(13, Sect) / 2 - (PileSect(6, 1) + PileSect(4, 1) / 2)) ^ 2 * (PileSect(9, Sect) / PileSect(10, Sect) - 1))
            FSA(j, 2) = EIG

        Else
            LatPile = "Invalid section type"
            Exit Function
        End If
    Next j


    PYA = PY_624(SoilTabs, YA, Loads, PYCurveA, KOption)
    NumPYPoints = UBound(PYA)
    For j = 1 To NumNodes

        FSA(j, 3) = PYA(j, 1)

    Next j

    k = 0
    NumLNodes = 1
    Do
        k = k + 1
        Call BoEF(FSA, LoadA, 0, 2, NumLNodes, SResA)
        NumLNodes = NumNodes

        YSum = 0
        YDiff = 0
        For j = 1 To NumNodes
            YSum = YSum + SResA(j, 2)
            YDiff = YDiff + Abs(YA(j, 3) - SResA(j, 2))
            YA(j, 3) = SResA(j, 2)
        Next j
        If YSum <> 0 Then YNorm = YDiff / YSum Else YNorm = 0

        PYA = PY_624(SoilTabs, YA, Loads, PYCurveA, KOption)
        StiffDiff = 0
        StiffSum = 0
        PStiffDiff = 0
        PStiffSum = 0

        Sect = 1
        For i = 1 To NumNodes
            Depth = FSA(i, 1)
            If Depth > (PileSect(1, Sect) + 0.000001) Then Sect = Sect + 1

            ' Apply node loads
            LoadA(1, i) = i
            AxLoad = Loads(3, 1) + AxGrad * Depth
            If AxLoad < Loads(4, 1) Then AxLoad = Loads(4, 1)
            If i > 1 Then LoadA(3, i) = AxLoad * (SResA(i - 1, 2) - SResA(i, 2))
            If i = 1 And SoilTabs(7, 1) = 3 Then
                FSA(1, 3) = 0
            Else
                n = (i - 1) * 2 + 1
                If Abs(SResA(i, 2)) <= LinLimits(i, 1) Then
                    FSA(i, 3) = LinLimits(i, 2)
                Else
                    NewStiff = PYA(i, 1)
                    StiffDiff = StiffDiff + Abs(FSA(i, 3) - NewStiff)
                    FSA(i, 3) = NewStiff
                    StiffSum = StiffSum + NewStiff
                End If
            End If

            ' Pile flexural stiffness
            mom = SResA(i, 3)
            If (UCase(PileSect(3, Sect)) = "C" Or UCase(PileSect(3, Sect)) = "R") Then
                ' If Abs(mom) < 0.1 Then
                FSA(i, 2) = EIG
                ' Else

                If UCase(PileSect(3, Sect)) = "C" Then
                    PileSect2(1, 1) = PileSect(2, Sect) * 1000
                    PileSect2(2, 1) = PileSect(4, Sect)
                    PileSect2(3, 1) = PileSect(5, Sect)
                    PileSect2(4, 1) = PileSect(6, Sect)
                    PileSect2(5, 1) = PileSect(7, Sect) / 1000
                    PileSect2(6, 1) = PileSect(8, Sect) / 1000
                    PileSect2(7, 1) = PileSect(9, Sect) / 1000
                    PileSect2(8, 1) = PileSect(10, Sect) / 1000
                    PileSect2(9, 1) = PileSect(11, Sect) / 1000
                    PileSect2(10, 1) = PileSect(12, Sect)

                    If Abs(mom) > 0.1 Then
                        Curve = CircE(PileSect2, AxLoad, mom, 6, Beta - Int(Beta))(6, 1)
                        NewEI = mom / Curve
                    Else
                        NewEI = CircE(PileSect2, AxLoad, mom, 0)(2, 1) * PileSect(10, Sect) / 1000000000000#

                    End If


                ElseIf UCase(PileSect(3, Sect)) = "R" Then
                    PileSect2(1, 1) = PileSect(13, Sect) * 1000
                    PileSect2(2, 1) = PileSect(2, Sect) * 1000
                    PileSect2(3, 1) = PileSect(4, Sect)
                    PileSect2(4, 1) = PileSect(5, Sect)
                    PileSect2(5, 1) = PileSect(6, Sect)
                    PileSect2(6, 1) = PileSect(4, Sect)
                    PileSect2(7, 1) = PileSect(5, Sect)
                    PileSect2(8, 1) = PileSect(6, Sect)
                    PileSect2(9, 1) = PileSect(7, Sect) / 1000
                    PileSect2(10, 1) = PileSect(8, Sect) / 1000
                    PileSect2(11, 1) = PileSect(9, Sect) / 1000
                    PileSect2(12, 1) = PileSect(10, Sect) / 1000
                    PileSect2(13, 1) = PileSect(11, Sect) / 1000
                    PileSect2(14, 1) = PileSect(12, Sect)


                    Curve = Estress(PileSect2, AxLoad, mom, 8, Beta, , 3)
                    If Curve(1, 1) <> "Uncracked" Then
                        NewEI = mom / Curve(1, 1)
                    Else
                        NewEI = Curve(1, 2) * PileSect(10, Sect) / 1000000000000#
                    End If
                End If

                If Abs(1 - NewEI / FSA(i, 2)) > 0.05 Then NewEI = (NewEI + FSA(i, 2)) / 2
                FSA(i, 2) = NewEI
            End If
            PStiffSum = PStiffSum + FSA(i, 2)
            PStiffDiff = PStiffDiff + Abs(FSA(i, 2) - FSA(i, 2))


            ' End If
        Next i
        If StiffSum > 0 Then StiffNorm = StiffDiff / StiffSum Else StiffNorm = 0
        If PStiffSum > 0 Then PStiffNorm = PStiffDiff / PStiffSum Else PStiffNorm = 0


    Loop While (StiffNorm > StiffTol Or PStiffNorm > PStiffTol Or YNorm > YTol) And k < MaxIts

    Select Case Out
    Case 1

        For i = 1 To NumNodes
            SResA(i, 1) = -FSA(i, 1)
            SResA(i, 5) = FSA(i, 2)
            SResA(i, 6) = FSA(i, 3)
        Next i
    
    Case 2
        For i = 1 To NumNodes
            SResA(i, 1) = -FSA(i, 1)
            SResA(i, 2) = FSA(i, 2)
            SResA(i, 3) = FSA(i, 3)

        Next i
        ReDim Preserve SResA(1 To NumNodes, 1 To 3)
       
Case 3
 ReDim Preserve SResA(1 To NumNodes, 1 To 11)
 For i = 1 To NumNodes
            SResA(i, 1) = -FSA(i, 1)
            SResA(i, 5) = FSA(i, 2)
            SResA(i, 6) = FSA(i, 3)
            SResA(i, 7) = PYA(i, 2)
            SResA(i, 8) = PYA(i, 3)
            SResA(i, 9) = PYA(i, 4)
            SResA(i, 10) = PYA(i, 5)
            SResA(i, 11) = PYA(i, 6)
            
        Next i
    
    
    End Select
    
     LatPile = SResA

End Function





