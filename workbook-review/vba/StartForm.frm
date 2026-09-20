Attribute VB_Name = "StartForm"
Attribute VB_Base = "0{FD94C0BE-D1C3-4946-9A52-992707E88B9D}{33C7DB31-F13B-4CCA-94EA-EA41C06D36E5}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = False
Private Sub CommandButton1_Click()
    Unload Me
End Sub

Private Sub CommandButton2_Click()
    Excel.ThisWorkbook.Close SaveChanges:=False
End Sub

