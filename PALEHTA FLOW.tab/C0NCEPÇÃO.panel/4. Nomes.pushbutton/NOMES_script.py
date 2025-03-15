# -*- coding: utf-8 -*-
from pyrevit import revit, DB

# Verificar se o documento do Revit está disponível
doc = revit.doc
if not doc:
    raise SystemExit

# Obtém a fase ativa do projeto
phases = list(doc.Phases)
if not phases:
    raise SystemExit
phase = phases[-1]  # Pega a última fase do projeto

# Função para obter o nome do ambiente externo da porta
def get_external_room(door):
    room = door.ToRoom[phase] if door.ToRoom else None  # Garante que está acessando na fase correta
    if room:
        param = room.LookupParameter("Nome")
        room_name = param.AsString() if param else None

        # Se não encontrou pelo LookupParameter, tenta pelo BuiltInParameter
        if not room_name:
            room_name = room.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString() if room.get_Parameter(DB.BuiltInParameter.ROOM_NAME) else "SAÍDA"

        return room_name
    return "SAÍDA"

# Função para verificar se a porta está espelhada e atualizar o parâmetro "INVERTER O TEXTO"
def check_mirrored_door(door):
    mirrored = door.Mirrored  # Verifica se a porta está espelhada
    param = door.LookupParameter("INVERTER O TEXTO")
    if param:
        param.Set(0 if mirrored else 1)  # Desmarca se espelhada, mantém se não espelhada

# Coletar todas as portas do projeto
doors_collector = DB.FilteredElementCollector(doc) \
                    .OfCategory(DB.BuiltInCategory.OST_Doors) \
                    .WhereElementIsNotElementType()

# Contar e atualizar o nome do ambiente externo no parâmetro "TEXTO DA PLACA"
t = DB.Transaction(doc, "Atualizar Texto da Placa")
t.Start()
try:
    for door in doors_collector:
        param = door.LookupParameter("TEXTO DA PLACA")
        if param:
            room_name = get_external_room(door)
            param.Set(room_name)
        
        # Verifica se a porta está espelhada e ajusta o parâmetro "INVERTER O TEXTO"
        check_mirrored_door(door)

    t.Commit()
except Exception as e:
    t.RollBack()
finally:
    if t.HasStarted():
        t.RollBack()
