# -*- coding: utf-8 -*-

from pyrevit import script
from Autodesk.Revit.DB import (
    FilteredElementCollector, BuiltInCategory, XYZ, BoundingBoxXYZ, 
    Transaction, ElementTransformUtils
)

# Obter o documento ativo
doc = __revit__.ActiveUIDocument.Document

# Obter todas as portas do modelo
portas = list(FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Doors).WhereElementIsNotElementType())

# Função otimizada para calcular a menor distância entre bounding boxes
def calcular_menor_distancia(bb1, bb2):
    distancias = [
        (abs(bb1.Min.X - bb2.Max.X), XYZ(bb2.Max.X - bb1.Min.X, 0, 0)),
        (abs(bb1.Max.X - bb2.Min.X), XYZ(bb2.Min.X - bb1.Max.X, 0, 0)),
        (abs(bb1.Min.Y - bb2.Max.Y), XYZ(0, bb2.Max.Y - bb1.Min.Y, 0)),
        (abs(bb1.Max.Y - bb2.Min.Y), XYZ(0, bb2.Min.Y - bb1.Max.Y, 0))
    ]
    return min(distancias, key=lambda x: x[0])[1]  # Retorna a direção do deslocamento

if portas:
    paredes = list(FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Walls).WhereElementIsNotElementType())

    t = Transaction(doc, "Alinhar Portas com Paredes Mais Próximas")
    t.Start()

    for porta in portas:
        porta_bounding_box = porta.get_BoundingBox(None)
        if not porta_bounding_box:
            continue
        
        parede_hospedeira = porta.Host if hasattr(porta, 'Host') else None
        menor_distancia = float('inf')
        parede_proxima = None
        deslocamento_final = XYZ(0, 0, 0)

        for parede in paredes:
            if parede_hospedeira and parede.Id == parede_hospedeira.Id:
                continue
            
            parede_bounding_box = parede.get_BoundingBox(None)
            if parede_bounding_box:
                deslocamento = calcular_menor_distancia(porta_bounding_box, parede_bounding_box)
                distancia = deslocamento.GetLength()
                if distancia < menor_distancia:
                    menor_distancia = distancia
                    parede_proxima = parede
                    deslocamento_final = deslocamento

        if parede_proxima and menor_distancia * 30.48 <= 200:
            try:
                ElementTransformUtils.MoveElement(doc, porta.Id, deslocamento_final)
            except:
                pass  # Em caso de erro, continua sem interromper o loop

    t.Commit()
