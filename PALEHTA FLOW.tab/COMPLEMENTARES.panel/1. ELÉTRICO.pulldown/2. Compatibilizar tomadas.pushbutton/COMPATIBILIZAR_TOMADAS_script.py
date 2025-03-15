# -- coding: utf-8 --
import clr
clr.AddReference("RevitServices")
clr.AddReference("RevitNodes")
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")
clr.AddReference("System.Windows.Forms")

from pyrevit import revit
from Autodesk.Revit.DB import *
from System.Windows.Forms import MessageBox

# Obter documento do Revit
doc = revit.doc
uidoc = revit.uidoc
view = doc.ActiveView  # Vista ativa

# Obtém todos os pilares do projeto
pilares = list(FilteredElementCollector(doc)
               .OfCategory(BuiltInCategory.OST_StructuralColumns)
               .WhereElementIsNotElementType()
               .ToElements())

# Obtém todos os dispositivos elétricos do projeto
dispositivos_eletricos = list(FilteredElementCollector(doc)
                              .OfCategory(BuiltInCategory.OST_ElectricalFixtures)
                              .WhereElementIsNotElementType()
                              .ToElements())

# Obtém todas as portas do projeto
portas = list(FilteredElementCollector(doc)
              .OfCategory(BuiltInCategory.OST_Doors)
              .WhereElementIsNotElementType()
              .ToElements())

# Obtém todas as janelas do projeto
janelas = list(FilteredElementCollector(doc)
               .OfCategory(BuiltInCategory.OST_Windows)
               .WhereElementIsNotElementType()
               .ToElements())

# Função para verificar interseção de bounding boxes
def verifica_intersecao(bbox1, bbox2):
    if not bbox1 or not bbox2:
        return False  # Evita erro se alguma bounding box for None
    return (bbox1.Min.X <= bbox2.Max.X and bbox1.Max.X >= bbox2.Min.X and
            bbox1.Min.Y <= bbox2.Max.Y and bbox1.Max.Y >= bbox2.Min.Y and
            bbox1.Min.Z <= bbox2.Max.Z and bbox1.Max.Z >= bbox2.Min.Z)

# Lista para armazenar os IDs dos dispositivos a serem deletados
dispositivos_para_deletar = set()

# Verifica a interseção entre pilares e dispositivos elétricos
for pilar in pilares:
    pilar_bbox = pilar.get_BoundingBox(None)
    if pilar_bbox:
        for dispositivo in dispositivos_eletricos:
            dispositivo_bbox = dispositivo.get_BoundingBox(None)
            if dispositivo_bbox and verifica_intersecao(pilar_bbox, dispositivo_bbox):
                dispositivos_para_deletar.add(dispositivo.Id)

# Verifica a interseção entre portas, janelas e dispositivos elétricos
for elemento in portas + janelas:
    elemento_bbox = elemento.get_BoundingBox(None)
    if elemento_bbox:
        for dispositivo in dispositivos_eletricos:
            dispositivo_bbox = dispositivo.get_BoundingBox(None)
            if dispositivo_bbox and verifica_intersecao(elemento_bbox, dispositivo_bbox):
                dispositivos_para_deletar.add(dispositivo.Id)

# Deleta os dispositivos elétricos que fazem interseção com os pilares, portas e janelas
if dispositivos_para_deletar:
    with Transaction(doc, "Deletar Dispositivos Elétricos em Interseção") as trans:
        trans.Start()
        elementos_excluidos = 0  # Contador de elementos deletados
        for dispositivo_id in dispositivos_para_deletar:
            elemento = doc.GetElement(dispositivo_id)
            if elemento and not elemento.Pinned:  # Garante que o elemento existe e não está fixado
                try:
                    doc.Delete(dispositivo_id)
                    elementos_excluidos += 1  # Incrementa o contador
                except:
                    pass  # Ignora erros sem imprimir mensagens
        trans.Commit()

# Mensagem de confirmação via MessageBox do Windows Forms
MessageBox.Show("{0} dispositivos elétricos foram removidos.".format(elementos_excluidos), "Processo Concluído")
