# -*- coding: utf-8 -*-
import clr

clr.AddReference("RevitServices")
from RevitServices.Persistence import DocumentManager

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, XYZ, Transaction, Level

# Importando a função correta para obter o documento do Revit
from pyrevit import revit

# Obter documento do Revit
doc = revit.doc
uidoc = revit.uidoc
view = doc.ActiveView  # Vista ativa

# Coletar todos os ambientes do modelo
rooms = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms).WhereElementIsNotElementType().ToElements()

if not rooms:
    print("❌ Nenhum ambiente encontrado no projeto.")
else:
    # Coletar todos os níveis do modelo e organizar por elevação (do mais baixo para o mais alto)
    levels = {lvl.Id: lvl for lvl in FilteredElementCollector(doc).OfClass(Level)}
    sorted_levels = sorted(levels.values(), key=lambda lvl: lvl.Elevation)  # Ordenação por altura (Térreo primeiro)

    # Criar um dicionário para armazenar os ambientes organizados por pavimento
    rooms_by_level = {lvl.Name: [] for lvl in sorted_levels}

    # Preencher o dicionário com os ambientes
    for room in rooms:
        level = room.Level
        if level:
            level_name = level.Name
            centroid = room.Location.Point if room.Location else XYZ(0, 0, 0)
            rooms_by_level[level_name].append((room, centroid))

    # Ordenar os ambientes dentro de cada pavimento (Baixo para Cima, Esquerda para Direita)
    for level_name in rooms_by_level:
        rooms_by_level[level_name].sort(key=lambda x: (x[1].Y, x[1].X))  # Baixo para cima, Esquerda para Direita

    # Criar uma transação para renomear os ambientes
    trans = Transaction(doc, "Renumeração de Ambientes")
    trans.Start()

    try:
        # Iniciar a contagem da numeração
        room_numbering = 1

        # Percorrer os pavimentos na ordem correta (Térreo para cima)
        for level in sorted_levels:
            level_name = level.Name
            if level_name in rooms_by_level:
                for room, _ in rooms_by_level[level_name]:
                    param = room.LookupParameter("Número")
                    if param:
                        param.Set(str(room_numbering))
                        room_numbering += 1

        # Finaliza a transação corretamente
        trans.Commit()
        print("✅ Ambientes renumerados com sucesso!")

    except Exception as e:
        print("⚠ Erro durante a renumeração: {}".format(e))
        trans.RollBack()  # Cancela a transação em caso de erro
