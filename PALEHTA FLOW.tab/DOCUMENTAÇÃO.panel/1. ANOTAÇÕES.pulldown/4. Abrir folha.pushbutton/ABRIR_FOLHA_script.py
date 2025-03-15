# -*- coding: utf-8 -*-

import clr
clr.AddReference("RevitServices")
clr.AddReference("RevitAPI")
clr.AddReference("System")

from pyrevit import revit
from Autodesk.Revit.DB import FilteredElementCollector, Viewport, ViewType

# Obter documento do Revit
doc = revit.doc
uidoc = revit.uidoc
view = doc.ActiveView  # Vista ativa

# Verificar se a vista está em uma folha
if view and view.ViewType not in [ViewType.DrawingSheet, ViewType.Schedule]:
    viewports = [vp for vp in FilteredElementCollector(doc).OfClass(Viewport) if vp.ViewId == view.Id]
    
    if viewports:
        sheet_id = viewports[0].SheetId
        sheet = doc.GetElement(sheet_id)
        if sheet:
            # Ativar a folha
            uidoc.RequestViewChange(sheet)
else:
    pass