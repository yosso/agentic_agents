Attribute VB_Name = "mCubic"

Public Function cubic(cparameters As Variant, Out As Long) As Double
' /*      eosutilities.cpp

'         A. R. Kovscek
'         Created: November 1, 1999
'         Last Update: November 1, 1999
'
'         Contains a set of mathematical utilities and functions for
'         conducting equation of state (EOS) calculations.

' //      This function calculates the roots of a cubic equation of the form
' //      y^3 + p*y^2 + q*y + r = 0.
' //      The parameters p, q, and r may be zero or nonzero.
' //      num_of_real roots returns exactly what it says

    Dim cparam As Variant, A As Double, B As Double, C As Double, D As Double
    Dim P As Double, q As Double, R As Double
    Dim psquared As Double, pcubed As Double, Alpha As Double, Beta As Double, roottest As Double
    Dim numrealroots As Long, tempvalue As Double, Phi As Double
    Dim root1 As Double, root2 As Double, root3 As Double, signA As Double, signB As Double


    cparam = cparameters.Value
    A = cparam(1, 1)
    B = cparam(2, 1)
    C = cparam(3, 1)
    D = cparam(4, 1)

    If A = 0 Then
        cubic = Quadratic(B, C, D, Out)
        Exit Function
    End If

    P = B / A
    q = C / A
    R = D / A
    '
    '         // compute the coefficients of the reduced cubic equation,
    '         // compute roottest to determine how many real roots
    psquared = P * P
    Alpha = (3# * q - psquared) / 3#
    pcubed = P * P * P
    Beta = (2# * pcubed - 9# * P * q + 27# * R) / 27#
    roottest = Beta * Beta / 4# + Alpha * Alpha * Alpha / 27#
    '         //cout << "alpha, beta, roottest =" << alpha << "," << beta << "," << roottest << endl;
    '
    '         // branch solution depending upon whether there are 3 or 1 real roots
    '         // note the backtransformation to the original coordinate y
    If (roottest < 0#) Then
        ' 3 real roots
        '         {
        numrealroots = 3
        tempvalue = -Alpha ^ 3 / 27#
        Phi = WorksheetFunction.Acos(-Beta * 0.5 / (tempvalue ^ 0.5))
        '
        tempvalue = 2 * (-Alpha / 3#) ^ 0.5
        root1 = tempvalue * Cos(Phi / 3#) - P / 3#
        root2 = tempvalue * Cos(Phi / 3# + 2# * Pi / 3#) - P / 3#
        root3 = tempvalue * Cos(Phi / 3# + 4# * Pi / 3#) - P / 3#

        '         }       //end roottest < 0.
        '
    ElseIf (roottest > 0#) Then

        '// 1 real root
        '         {
        numrealroots = 1
        root2 = 0
        root3 = 0#
        '
        A = -0.5 * Beta + (roottest) ^ 0.5
        signA = A / Abs(A)
        A = Abs(A)
        A = signA * (A ^ (1 / 3))
        '
        B = -0.5 * Beta - (roottest) ^ 0.5
        signB = B / Abs(B)
        B = Abs(B)
        B = signB * (B ^ (1 / 3))
        '
        root1 = A + B - P / 3#

        '                 //cout << "A B = " << A << " " << B << endl;
        '         }       //end roottest > 0.
        '
    Else
        ' // 3 real, 2 equal roots
        '         {
        root3 = 0#
        '
        A = -0.5 * Beta + (roottest) ^ 0.5
        signA = A / Abs(A)
        A = Abs(A)
        A = signA * (A ^ (1 / 3))
        B = A
        '
        root1 = A + B
        root2 = -(A + B) / 2#
        '
        If Not (root1 = 0#) Then
            '                 {
            root1 = root1 - P / 3#
            root2 = root2 - P / 3#
            numrealroots = 2
            '                 }
        Else
            '                 {
            root1 = -P / 3#
            root2 = 0#
            numrealroots = 2

        End If
    End If

    '                 }
    '         }       // end roottest = 0.

    If Out = 1 Then
        cubic = root1
    ElseIf Out = 2 Then
        cubic = root2
    ElseIf Out = 3 Then
        cubic = root3
    Else
        cubic = numrealroots
    End If
    GoTo Endfunc
zero:

    cubic = xlErrValue



Endfunc:
End Function



Public Sub cubicsub(A, B, C, D, numrealroots, root1, root2, root3)

    Dim P, q, R, psquared, Alpha, Beta, pcubed, tempvalue, roottest, Phi, E, signE, F, signF As Double


    P = B / A
    q = C / A
    R = D / A
    '
    '         // compute the coefficients of the reduced cubic equation,
    '         // compute roottest to determine how many real roots
    psquared = P * P
    Alpha = (3# * q - psquared) / 3#
    pcubed = P * P * P
    Beta = (2# * pcubed - 9# * P * q + 27# * R) / 27#
    roottest = Beta * Beta / 4# + Alpha * Alpha * Alpha / 27#
    '         //cout << "alpha, beta, roottest =" << alpha << "," << beta << "," << roottest << endl;
    '
    '         // branch solution depending upon whether there are 3 or 1 real roots
    '         // note the backtransformation to the original coordinate y
    If (roottest < 0#) Then
        ' 3 real roots
        '         {
        numrealroots = 3
        tempvalue = -Alpha * Alpha * Alpha / 27#
        Phi = WorksheetFunction.Acos(-Beta * 0.5 / (tempvalue ^ 0.5))
        '
        tempvalue = 2 * (-Alpha / 3#) ^ 0.5
        root1 = tempvalue * Cos(Phi / 3#) - P / 3#
        root2 = tempvalue * Cos(Phi / 3# + 2# * Pi / 3#) - P / 3#
        root3 = tempvalue * Cos(Phi / 3# + 4# * Pi / 3#) - P / 3#

        '         }       //end roottest < 0.
        '
    ElseIf (roottest > 0#) Then

        '// 1 real root
        '         {
        numrealroots = 1
        root2 = 0
        root3 = 0#
        '
        E = -0.5 * Beta + (roottest) ^ 0.5
        signE = E / Abs(E)
        E = Abs(E)
        E = signE * (E ^ (1 / 3))
        '
        F = -0.5 * Beta - (roottest) ^ 0.5
        signF = F / Abs(F)
        F = Abs(F)
        F = signF * (F ^ (1 / 3))
        '
        root1 = E + F - P / 3#

        '                 //cout << "A B = " << A << " " << B << endl;
        '         }       //end roottest > 0.
        '
    Else
        ' // 3 real, 2 equal roots
        '         {
        root3 = 0#
        '
        E = -0.5 * Beta + (roottest) ^ 0.5
        signE = E / Abs(E)
        E = Abs(E)
        E = signE * (E ^ (1 / 3))
        F = E
        '
        root1 = E + F
        root2 = -(E + F) / 2#
        '
        If Not (root1 = 0#) Then
            '                 {
            root1 = root1 - P / 3#
            root2 = root2 - P / 3#
            numrealroots = 2
            '                 }
        Else
            '                 {
            root1 = -P / 3#
            root2 = 0#
            numrealroots = 1

        End If
    End If

    '                 }
    '         }       // end roottest = 0.

End Sub

Function Quadratic(A As Double, B As Double, C As Double, Optional Out As Long) As Variant

' * Copyright (C) 2006 Interactive Design Services Pty Ltd

'  This program is free software; you can redistribute it and/or modify
'  it under the terms of the GNU General Public License as published by
'  the Free Software Foundation; either version 2 of the License, or (at
'  your option) any later version.

'  This program is distributed in the hope that it will be useful, but
'  WITHOUT ANY WARRANTY; without even the implied warranty of
'  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
'  General Public License for more details.

'  You should have received a copy of the GNU General Public License
'  along with this program; if not, write to the Free Software
'  Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.


'quadratic - finds the roots of  a x^2 + b x + c = 0

    Dim disc As Double, SqrtDisc As Double, QuadA(1 To 3, 1 To 1) As Variant, QuadAI(1 To 3, 1 To 1) As Variant

    If Out < -3 Then
        Quadratic = CVErr(xlErrNA)
        Exit Function
    End If

    If A = 0 Then

        QuadA(1, 1) = -C / B
        QuadA(2, 1) = 0
        QuadA(3, 1) = 1

    Else

        disc = B ^ 2 - 4 * A * C
        If disc >= 0 Then SqrtDisc = disc ^ 0.5 Else SqrtDisc = (-disc) ^ 0.5

        If disc >= 0 Then
            QuadA(1, 1) = (-B - SqrtDisc) / (2 * A)
            QuadA(2, 1) = (-B + SqrtDisc) / (2 * A)
            QuadA(3, 1) = 2
        Else
            QuadA(1, 1) = (-B) / (2 * A)
            QuadA(2, 1) = (-B) / (2 * A)
            QuadA(3, 1) = 0
            QuadAI(1, 1) = (-SqrtDisc) / (2 * A)
            QuadAI(2, 1) = (SqrtDisc) / (2 * A)
            QuadAI(3, 1) = 2
        End If
    End If

    If Out < -1 Then
        Quadratic = QuadAI(-Out, 1)
    ElseIf Out = -1 Then
        Quadratic = QuadAI
    ElseIf Out = 0 Then
        Quadratic = QuadA
    Else
        Quadratic = QuadA(Out, 1)
    End If

End Function


