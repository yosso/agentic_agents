Attribute VB_Name = "SmithP43"
Option Explicit

Option Base 1
Function BoEFA(BeamA As Variant, LoadA As Variant, Optional FixedNodes As Variant, Optional NIP As Long = 2) As Variant
    Dim NumNodes As Long, Resa() As Double, Loaded_Nodes As Long

    If TypeName(BeamA) = "Range" Then BeamA = BeamA.Value2
    If TypeName(LoadA) = "Range" Then LoadA = LoadA.Value2
    If TypeName(FixedNodes) = "Range" Then FixedNodes = FixedNodes.Value2
    Loaded_Nodes = 1

    NumNodes = UBound(BeamA)
    If IsMissing(FixedNodes) = True Then FixedNodes = 0

    ReDim ResBa(1 To NumNodes, 1 To 4)
    Call BoEF(BeamA, LoadA, FixedNodes, NIP, Loaded_Nodes, Resa)

    BoEFA = Resa

End Function

' Programs in this module are based on Fortran programs taken from "Prgramming The Finite Element Method"
' by IM Smith ans D.V. Griffiths, published by John Wiley & Sons


Sub BoEF(BeamA As Variant, LoadA As Variant, FixedNodeA As Variant, NIP As Long, Loaded_Nodes As Long, Resa() As Double)

    Dim nels As Long, neq As Long, nn As Long, nband As Long, nr As Long
    Dim iel As Long, i As Long, j As Long, k As Long, l As Long
    Dim fixed_nodes As Long, FixedCols As Long, Sense As Long, Value As Double, Node As Long
    Dim fs As Double, fs0 As Double, fs1 As Double, X As Double, samp_pt As Double, EI0 As Double, EI1 As Double, EI As Double

    Dim km() As Double, mm() As Double, eld() As Double, kv() As Double, Loads() As Double, coord() As Double
    Dim action As Variant, g_coord() As Double, ftf() As Double, dtd() As Double
    Dim der2() As Double, fun() As Double, mom() As Double, store_km() As Double, points() As Double
    Dim weights() As Double, ell() As Double
    Dim nf() As Long, g() As Long, num() As Long, g_num() As Long, no() As Long, g_g() As Long
    Dim etype() As Long, n As Long

    Const nod As Long = 2, nodof As Long = 2, ndof As Long = 4, ndim As Long = 1
    Const element As String = "line"

    If TypeName(BeamA) = "Range" Then BeamA = BeamA.Value2
    If TypeName(FixedNodeA) = "Range" Then FixedNodeA = FixedNodeA.Value2
    If TypeName(LoadA) = "Range" Then LoadA = LoadA.Value2

    ' Loaded_Nodes = UBound(LoadA, 2)
    nels = UBound(BeamA) - 1
    If NIP < 2 Then NIP = 2
    If NIP > 6 Then NIP = 6

    nn = nels + 1


    ReDim nf(nodof, nn)
    ReDim km(ndof, ndof)
    ReDim coord(nod, ndim)
    ReDim g_coord(ndim, nn)
    ReDim eld(ndof)
    ReDim g_num(nod, nels)
    ReDim num(nod)
    ReDim g(ndof)
    ReDim g_g(ndof, nels)
    ReDim mm(ndof, ndof)
    ReDim ftf(ndof, ndof)
    ReDim ell(nels)
    ReDim dtd(ndof, ndof)
    ReDim store_km(ndof, ndof, nels)
    ReDim der2(ndof)
    ReDim fun(ndof)
    ReDim mom(nn)
    ReDim points(NIP, ndim)
    ReDim weights(NIP)
    ReDim etype(nels)

    fs0 = BeamA(1, 3)
    fs1 = BeamA(2, 3)
    EI = BeamA(1, 2)

    For i = 1 To nels
        ell(i) = BeamA(i + 1, 1) - BeamA(i, 1)
        etype(i) = 1
    Next i
    nr = 0

    For i = 1 To nodof
        For j = 1 To nn
            nf(i, j) = 1
        Next j
    Next i

    If nr > 0 Then
        'read(10,*)(k,nf(:,k),i=1,nr)
    End If
    Call formnf(nf)
    neq = WorksheetFunction.Max(nf)

    '!--------------loop the elements to find global array sizes--------------------
    nband = 0

    For iel = 1 To nels
        Call geometry_2l(iel, ell(iel), coord, num)
        Call num_to_g(num, nf, g, ndof)

        For i = 1 To nod
            g_num(i, iel) = num(i)
        Next i

        For j = 1 To nod
            g_coord(1, num(j)) = coord(j, 1)
        Next j

        For i = 1 To ndof
            g_g(i, iel) = g(i)
        Next i


        If nband < bandwidth(g) Then nband = bandwidth(g)
    Next iel

    ReDim kv(neq * (nband + 1))
    ReDim Loads(0 To neq)

    Call sample(element, points, weights)

    X = 0#

    For iel = 1 To nels
        ReDim km(ndof, ndof)
        ReDim mm(ndof, ndof)
        For i = 1 To ndof
            g(i) = g_g(i, iel)
        Next i

        fs0 = BeamA(iel, 3)
        fs1 = BeamA(iel + 1, 3)
        EI0 = BeamA(iel, 2)
        EI1 = BeamA(iel + 1, 2)
        For i = 1 To NIP
            samp_pt = ell(iel) * 0.5 * (points(i, 1) + 1#)
            fs = samp_pt / (ell(iel)) * (fs1 - fs0) + fs0
            EI = samp_pt / (ell(iel)) * (EI1 - EI0) + EI0
            Call fmbeam(der2, fun, points, i, ell(iel))
            For k = 1 To ndof
                For l = 1 To ndof
                    ftf(k, l) = fun(k) * fun(l) * weights(i) * 0.5 * ell(iel) * fs
                    dtd(k, l) = der2(k) * der2(l) * weights(i) * 8# * EI / (ell(iel) ^ 3)
                    mm(k, l) = mm(k, l) + ftf(k, l)
                    km(k, l) = km(k, l) + dtd(k, l)

                Next l
            Next k
        Next i

        For i = 1 To ndof
            For j = 1 To ndof
                km(i, j) = km(i, j) + mm(i, j)
                store_km(i, j, iel) = km(i, j)
            Next j
        Next i

        X = BeamA(iel, 1)
        Call formkv(kv, km, g, neq, iel)
    Next iel

    '!-----------------------------read loads---------------------------------------

    If Loaded_Nodes <> 0 Then

        For i = 1 To Loaded_Nodes
            k = LoadA(1, i)
            Loads(nf(1, k)) = LoadA(2, i)
            Loads(nf(2, k)) = -LoadA(3, i)
        Next i
    End If

    'read (10,*)fixed_nodes
    If IsArray(FixedNodeA) = True Then
        fixed_nodes = UBound(FixedNodeA)
        FixedCols = UBound(FixedNodeA, 2)
    Else
        fixed_nodes = 0
    End If

    If fixed_nodes <> 0 Then
        For i = 1 To fixed_nodes
            Node = FixedNodeA(i, 1)
            Sense = 0
            If FixedNodeA(i, 2) = 1 Then Sense = 1
            If FixedNodeA(i, 3) = 1 Then Sense = Sense + 2
            If Sense = 1 Or Sense = 3 Then
                If FixedCols > 3 Then Value = FixedNodeA(i, 4) Else Value = 0
                n = nf(1, Node)
                kv(n) = kv(n) + 1E+20
                Loads(n) = kv(n) * Value
                Sense = Sense - 1
            End If
            If Sense = 2 Then
                If FixedCols > 4 Then Value = FixedNodeA(i, 5) Else Value = 0
                n = nf(2, Node)
                kv(n) = kv(n) + 1E+20
                Loads(n) = kv(n) * Value
            End If
        Next i

    End If

    '!-----------------------------equation solution -------------------------------
    Call banred(kv, neq)
    Call bacsub(kv, Loads)

    '!-----------------------retrieve element end actions---------------------------
    For iel = 1 To nels
        For i = 1 To ndof
            For j = 1 To ndof
                km(i, j) = store_km(i, j, iel)
            Next j
            g(i) = g_g(i, iel)
            eld(i) = Loads(g(i))
        Next i


        action = MATMUL(km, eld)
        Resa(iel, 3) = -action(2)
        Resa(iel, 4) = action(1)

    Next iel
    Resa(iel, 3) = -action(4)
    Resa(iel, 4) = -action(3)
    For i = 1 To nn
        Resa(i, 1) = BeamA(i, 1)
        Resa(i, 2) = Loads(2 * i - 1)
    Next i

End Sub


Sub formnf(nf)

'  ! reform nf
    Dim i As Long, j As Long, m As Long
    m = 0
    For j = 1 To UBound(nf, 2)
        For i = 1 To UBound(nf, 1)
            If (nf(i, j) <> 0) Then
                m = m + 1
                nf(i, j) = m
            End If
        Next i
    Next j

End Sub


'!----------------Node to freedom number conversion ----------------------------
Sub num_to_g(num, nf, g, ndof)

' !finds the g vector from num and nf
    Dim i As Long, j As Long, k As Long, nod As Long, nodof As Long

    nod = UBound(num, 1)
    nodof = UBound(nf, 1)
    For i = 1 To nod
        k = i * nodof
        For j = 1 To nodof
            g(k - nodof + j) = nf(j, num(i))
        Next j
    Next i

End Sub


' !-------------------------------- Lines  --------------------------------------

Sub geometry_2l(iel, ell, coord, num)

' ! node numbers, nodal coordinates and steering vectors for
' ! a line of (nonuniform) beam elements
    num(1) = iel
    num(2) = iel + 1
    If (iel = 1) Then
        coord(1, 1) = 0#
        coord(2, 1) = ell
    Else
        coord(1, 1) = coord(2, 1)
        coord(2, 1) = coord(2, 1) + ell
    End If
End Sub

Sub rod_km(km, ea, Length)

    Dim Stiff As Double
    Stiff = ea / Length
    km(1, 1) = Stiff
    km(2, 2) = Stiff
    km(1, 2) = -Stiff
    km(2, 1) = -Stiff

End Sub

Sub formkv(bk, km, g, n, iel)

' !global stiffness matrix stored as a vector (upper triangle)
    Dim idof As Long, i As Long, j As Long, icd As Long, ival As Long
    idof = UBound(km, 1) - LBound(km, 1) + 1

    For i = 1 To idof
        If (g(i) <> 0) Then
            For j = 1 To idof
                If (g(j) <> 0) Then
                    icd = g(j) - g(i) + 1
                    If (icd - 1 >= 0) Then
                        ival = n * (icd - 1) + g(i)
                        bk(ival) = bk(ival) + km(i, j)
                    End If
                End If
            Next j

        End If

    Next i


    ' Return
End Sub


Sub banred(bk, n)

' ! gaussian reduction on a vector stored as an upper triangle
    Dim i As Long, il1 As Long, kbl As Long, j As Long, ij As Long, nkb As Long, m As Long, ni As Long, nj As Long, iw As Long
    Dim sum As Double

    iw = UBound(bk, 1) / n - 1
    For i = 2 To n
        il1 = i - 1
        kbl = il1 + iw + 1
        If (kbl - n > 0) Then kbl = n
        For j = i To kbl
            ij = (j - i) * n + i
            sum = bk(ij)
            nkb = j - iw
            If (nkb <= 0) Then nkb = 1
            If (nkb - il1 <= 0) Then
                For m = nkb To il1
                    ni = (i - m) * n + m
                    nj = (j - m) * n + m
                    sum = sum - bk(ni) * bk(nj) / bk(m)
                Next m
            End If
            bk(ij) = sum
        Next j
    Next i

End Sub

Sub bacsub(bk, Loads)


' ! performs the complete gaussian backsubstitution
    Dim nkb As Long, k As Long, i As Long, jn As Long, jj As Long, i1 As Long, n As Long, iw As Long
    Dim sum As Double
    n = UBound(Loads, 1)
    iw = UBound(bk, 1) / n - 1
    Loads(1) = Loads(1) / bk(1)
    For i = 2 To n
        sum = Loads(i)
        i1 = i - 1
        nkb = i - iw
        If (nkb <= 0) Then nkb = 1
        For k = nkb To i1
            jn = (i - k) * n + k
            sum = sum - bk(jn) * Loads(k)
        Next k
        Loads(i) = sum / bk(i)
    Next i
    For jj = 2 To n
        i = n - jj + 1
        sum = 0#
        i1 = i + 1
        nkb = i + iw
        If (nkb - n > 0) Then nkb = n
        For k = i1 To nkb
            jn = (k - i) * n + i
            sum = sum + bk(jn) * Loads(k)
        Next k
        Loads(i) = Loads(i) - sum / bk(i)
    Next jj
    ' Return
End Sub


Function MATMUL(A, B)
'
'      PRODUCT OF TWO MATRICES
'
    Dim i As Long, j As Long, k As Long, X As Double, l As Long, n As Long
    l = UBound(A, 2)
    n = UBound(A)
    ReDim Mat(l) As Double
    For i = 1 To l
        For j = 1 To n
            X = 0#
            For k = 1 To l
                X = X + A(i, k) * B(k)
            Next k
            Mat(i) = X
        Next j
    Next i
    MATMUL = Mat
End Function


'
Sub MATRAN(A, IA, B, IB, m, n)
'
'      FORMS THE TRANSPOSE OF A MATRIX
'
'     REAL A(IA,*),B(IB,*)
'     DO 1 I = 1,M
'         DO 1 J = 1,N
'     A(j, i) = B(i, j)

End Sub

Sub MSMULT(A, IA, C, m, n)
'
'      MULTIPLIES A MATRIX BY A SCALAR
'
'      REAL A(IA,*)
'      DO 1 I = 1,M
'          DO 1 J = 1,N
'     A(i, j) = A(i, j) * c
End Sub

Sub MVMULT(m, v, k, l, Y)

'      MULTIPLIES A MATRIX BY A VECTOR


    Dim i As Long, j As Long, X As Double
    ' ReDim Preserve M(k, l), V(l), Y(k)
    ReDim Y(k)
    For i = 1 To k
        X = 0#
        For j = 1 To l
            X = X + m(i, j) * v(j)
        Next j
        Y(i) = X
    Next i
End Sub

Function bandwidth(g)


'! finds the element bandwidth from g
    If WorksheetFunction.Min(g) > 0 Then
        bandwidth = WorksheetFunction.Max(g) - WorksheetFunction.Min(g)
    Else
        bandwidth = 0
    End If
End Function


Sub sample(element, s, wt)

' ! returns the local coordinates of the integrating points

' ****  Edited for line element only  *****

    Dim NIP As Long, root3 As Double, R15 As Double, W(1 To 3) As Double, v(1 To 9) As Double, B As Double, C As Double, i As Long

    root3 = 1# / (3#) ^ 0.5
    R15 = 0.2 * (15#) ^ 0.5
    NIP = UBound(s, 1)
    W(1) = 5# / 9#
    W(2) = 8# / 9#
    W(3) = 5# / 9#
    For i = 1 To 7 Step 3
        v(i) = 5# / 9# * W(1)
        v(i + 1) = 8# / 9# * W(2)
        v(i + 2) = 5# / 9# * W(3)
    Next i
    Select Case element
    Case "line"

        Select Case (NIP)
        Case (1)
            s(1, 1) = 0#
            wt(1) = 2#
        Case (2)
            s(1, 1) = root3
            s(2, 1) = -s(1, 1)
            wt(1) = 1#
            wt(2) = 1#
        Case (3)
            s(1, 1) = R15
            s(2, 1) = 0#
            s(3, 1) = -s(1, 1)
            wt = W
        Case (4)
            s(1, 1) = 0.861136311594053
            s(2, 1) = 0.339981043584856
            s(3, 1) = -s(2, 1)
            s(4, 1) = -s(1, 1)

            wt(1) = 0.347854845137454
            wt(2) = 0.652145154862546
            wt(3) = wt(2)
            wt(4) = wt(1)
        Case (5)
            s(1, 1) = 0.906179845938664
            s(2, 1) = 0.538469310105683
            s(3, 1) = 0#
            s(4, 1) = -s(2, 1)
            s(5, 1) = -s(1, 1)
            wt(1) = 0.236926885056189
            wt(2) = 0.478628670499366
            wt(3) = 0.568888888888889
            wt(4) = wt(2)
            wt(5) = wt(1)
        Case (6)
            s(1, 1) = 0.932469514203152
            s(2, 1) = 0.661209386466265
            s(3, 1) = 0.238619186083197
            s(4, 1) = -s(3, 1)
            s(5, 1) = -s(2, 1)
            s(6, 1) = -s(1, 1)
            wt(1) = 0.17132449237917
            wt(2) = 0.360761573048139
            wt(3) = 0.467913934572691
            wt(4) = wt(3)
            wt(5) = wt(2)
            wt(6) = wt(1)
        Case Default
            '      print*,"wrong number of integrating points for a line"
        End Select
    End Select

End Sub


Sub fmbeam(der2, fun, points, i, ell)


' !
' ! this subroutine forms the beam shape functions
' ! and their 2nd derivatives in local coordinates
' !

    Dim xi As Double, xi2 As Double, xi3

    xi = points(i, 1)
    xi2 = xi * xi
    xi3 = xi2 * xi

    fun(1) = 0.25 * (xi3 - 3# * xi + 2#)
    fun(2) = 0.125 * ell * (xi3 - xi2 - xi + 1#)
    fun(3) = 0.25 * (-xi3 + 3# * xi + 2#)
    fun(4) = 0.125 * ell * (xi3 + xi2 - xi - 1#)
    der2(1) = 1.5 * xi
    der2(2) = 0.25 * ell * (3# * xi - 1#)
    der2(3) = -1.5 * xi
    der2(4) = 0.25 * ell * (3# * xi + 1#)


End Sub


