# -*- coding: utf-8 -*-
from Autodesk.Revit.DB import (
    FilteredElementCollector,
    Transaction,
    JoinGeometryUtils,
    BuiltInCategory,
    BoundingBoxXYZ
)
from pyrevit import revit

# Obtém o documento ativo no Revit
doc = revit.doc

# Lista de categorias que podem ser unidas
CATEGORIAS_UNIVEIS = [
    BuiltInCategory.OST_Walls,  # Paredes
    BuiltInCategory.OST_Floors,  # Pisos
    BuiltInCategory.OST_StructuralColumns,  # Pilares
    BuiltInCategory.OST_StructuralFraming,  # Vigas
    BuiltInCategory.OST_Roofs  # Telhados
]

# Lista de categorias específicas para ajuste de ordem
CATEGORIA_PISOS = BuiltInCategory.OST_Floors
CATEGORIA_PILARES = BuiltInCategory.OST_StructuralColumns
CATEGORIA_VIGAS = BuiltInCategory.OST_StructuralFraming

# Função para obter elementos por categoria
def obter_elementos(categoria):
    return list(FilteredElementCollector(doc)
                .OfCategory(categoria)
                .WhereElementIsNotElementType()
                .ToElements())

# Função para verificar se os Bounding Boxes dos elementos realmente se tocam
def bounding_boxes_intersect(bbox1, bbox2):
    if bbox1 is None or bbox2 is None:
        return False
    if bbox1.Min.X > bbox2.Max.X or bbox1.Max.X < bbox2.Min.X:
        return False
    if bbox1.Min.Y > bbox2.Max.Y or bbox1.Max.Y < bbox2.Min.Y:
        return False
    if bbox1.Min.Z > bbox2.Max.Z or bbox1.Max.Z < bbox2.Min.Z:
        return False
    return True

# 1️⃣ Função para unir todos os elementos que podem ser unidos
def unir_todos_os_elementos():
    elementos = []
    for categoria in CATEGORIAS_UNIVEIS:
        elementos += obter_elementos(categoria)

    t = Transaction(doc, "Unir Todos os Elementos")
    t.Start()
    for i in range(len(elementos)):
        for j in range(i + 1, len(elementos)):
            elem1 = elementos[i]
            elem2 = elementos[j]

            bbox1 = elem1.get_BoundingBox(None)
            bbox2 = elem2.get_BoundingBox(None)

            # Verifica se os elementos estão próximos antes de unir
            if bounding_boxes_intersect(bbox1, bbox2):
                try:
                    if not JoinGeometryUtils.AreElementsJoined(doc, elem1, elem2):
                        JoinGeometryUtils.JoinGeometry(doc, elem1, elem2)
                except:
                    pass  # Ignora erros
    t.Commit()

# 2️⃣ Função para corrigir a ordem da união (pilares/vigas cortam pisos)
def corrigir_ordem_uniao(lista_cortadores, lista_cortados, nome_transacao):
    t = Transaction(doc, nome_transacao)
    t.Start()
    for cortador in lista_cortadores:
        for cortado in lista_cortados:
            try:
                # Obtém os bounding boxes dos elementos
                bbox1 = cortador.get_BoundingBox(None)
                bbox2 = cortado.get_BoundingBox(None)

                # Se os elementos não se tocam, não tenta unir (evita o aviso do Revit)
                if not bounding_boxes_intersect(bbox1, bbox2):
                    continue

                # 1️⃣ Se os elementos já estão unidos, primeiro remove a união
                if JoinGeometryUtils.AreElementsJoined(doc, cortado, cortador):
                    JoinGeometryUtils.UnjoinGeometry(doc, cortado, cortador)  # Remove a união na ordem errada
                
                # 2️⃣ Agora une novamente na ordem correta (cortador primeiro, cortado depois)
                if not JoinGeometryUtils.AreElementsJoined(doc, cortador, cortado):
                    JoinGeometryUtils.JoinGeometry(doc, cortador, cortado)

                # 3️⃣ Garante que a união não está invertida
                JoinGeometryUtils.SwitchJoinOrder(doc, cortador, cortado)

            except Exception as e:
                print("Erro ao corrigir união entre {} e {}: {}".format(cortador.Id, cortado.Id, e))
    t.Commit()

# Executa a união de todos os elementos
unir_todos_os_elementos()

# Obtém os elementos divididos por categorias específicas para corrigir a ordem
pisos = obter_elementos(CATEGORIA_PISOS)
pilares = obter_elementos(CATEGORIA_PILARES)
vigas = obter_elementos(CATEGORIA_VIGAS)

# 3️⃣ Ajustar a união para que Pilares cortem Pisos
corrigir_ordem_uniao(pilares, pisos, "Ajustar União: Pilares cortam Pisos")

# 4️⃣ Ajustar a união para que Vigas cortem Pisos
corrigir_ordem_uniao(vigas, pisos, "Ajustar União: Vigas cortam Pisos")
