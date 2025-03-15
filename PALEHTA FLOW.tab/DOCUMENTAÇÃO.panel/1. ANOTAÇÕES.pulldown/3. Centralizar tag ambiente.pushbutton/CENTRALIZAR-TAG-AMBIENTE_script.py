# -*- coding: utf-8 -*-

# IMPORTA��ES NECESS�RIAS
import clr
clr.AddReference("RevitAPI")
clr.AddReference("RevitServices")
from Autodesk.Revit.DB import *
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager
from pyrevit import revit

# OBTER DOCUMENTO DO REVIT
doc = revit.doc
uidoc = revit.uidoc
view = doc.ActiveView  # Vista ativa

# FUN��O PARA OBTER O CENTRO DO AMBIENTE
def obter_centro_ambiente(room):
    bbox = room.BoundingBox[view]
    if bbox:
        centro_x = (bbox.Min.X + bbox.Max.X) / 2
        centro_y = (bbox.Min.Y + bbox.Max.Y) / 2
        return XYZ(centro_x, centro_y, 0)  # Define o Z como 0 para evitar problemas
    return None

# FUN��O PARA AJUSTAR A POSI��O DO NOME DO AMBIENTE E A LOCALIZA��O DA TAG
def ajustar_posicao_ambiente_e_tag():
    try:
        # FILTRAR APENAS AMBIENTES
        collector = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms).WhereElementIsNotElementType()
        rooms = list(collector)
        
        if not rooms:
            print("Nenhum ambiente encontrado no projeto.")
            return
        
        # FILTRAR AS TAGS DOS AMBIENTES
        tag_collector = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_RoomTags).WhereElementIsNotElementType()
        room_tags = {tag.Room.Id.IntegerValue: tag for tag in tag_collector if tag.Room}
        
        # INICIAR TRANSA��O
        t = Transaction(doc, "Ajustar posi��o dos ambientes e tags")
        t.Start()
        
        for room in rooms:
            centro = obter_centro_ambiente(room)
            if centro and isinstance(room.Location, LocationPoint):
                room.Location.Point = centro  # Move o ponto de localiza��o
                print("Ambiente '{}' ajustado para o centro.".format(room.get_Parameter(BuiltInParameter.ROOM_NAME).AsString()))
            
            # AJUSTAR POSI��O DA TAG SE EXISTIR
            room_id = room.Id.IntegerValue
            if room_id in room_tags:
                tag = room_tags[room_id]
                tag.Location.Move(centro - tag.Location.Point)
                print("Tag do ambiente '{}' ajustada para o centro.".format(room.get_Parameter(BuiltInParameter.ROOM_NAME).AsString()))
        
        # FINALIZAR TRANSA��O
        t.Commit()
        print("Posi��o dos ambientes e tags ajustada com sucesso!")
    
    except Exception as e:
        print("Erro ao ajustar posi��o dos ambientes e tags: ", str(e))
        if t.HasStarted():
            t.RollBack()

# EXECUTAR FUN��O
ajustar_posicao_ambiente_e_tag()