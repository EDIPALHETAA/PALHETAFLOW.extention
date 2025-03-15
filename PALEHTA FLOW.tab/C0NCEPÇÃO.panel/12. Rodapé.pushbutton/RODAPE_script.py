# -*- coding: utf-8 -*-

import clr
import sys
import System
from System.Collections.Generic import *

clr.AddReference("RevitServices")
clr.AddReference("RevitAPI")
clr.AddReference("RevitNodes")
clr.AddReference("System")
clr.AddReference("System.Windows.Forms")

from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import *
from System.Windows.Forms import MessageBox
from pyrevit import forms

# Obtém o documento ativo
uidoc = __revit__.ActiveUIDocument if hasattr(__revit__, 'ActiveUIDocument') else None
doc = uidoc.Document if uidoc else None
vista_atual = uidoc.ActiveView if uidoc else None
uiapp = __revit__
app = uiapp.Application

if doc is None:
    MessageBox.Show("Nenhum documento ativo encontrado. Abra um projeto no Revit antes de executar o script.", "Erro")
    raise SystemExit

# Buscar o tipo de parede "POLIESTIRENO"
def obter_tipo_de_parede_por_nome(nome_parede):
    for tipo in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Walls).OfClass(WallType).WhereElementIsElementType():
        if tipo.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString() == nome_parede:
            return tipo
    return None

selected_wall_type_obj = obter_tipo_de_parede_por_nome("POLIESTIRENO")
if not selected_wall_type_obj:
    MessageBox.Show("O tipo de parede 'POLIESTIRENO' não foi encontrado no projeto.", "Erro")
    raise SystemExit

# Verificar se o tipo de parede tem a espessura definida
param_espessura = selected_wall_type_obj.get_Parameter(BuiltInParameter.WALL_ATTR_WIDTH_PARAM)
if param_espessura and param_espessura.HasValue:
    wall_thickness = param_espessura.AsDouble()
else:
    wall_thickness = UnitUtils.ConvertToInternalUnits(0.02, UnitTypeId.Meters)  # Valor padrão de 2 cm

# Definir altura fixa de 10 cm
altura_parede_cm = 10
altura_parede_m = altura_parede_cm / 100.0

definir_altura_parede = UnitUtils.ConvertToInternalUnits(altura_parede_m, UnitTypeId.Meters)

# Obtém os ambientes visíveis na vista ativa
def obter_ambientes_visiveis():
    """Obtém os ambientes (Rooms) visíveis na vista ativa do usuário no Revit."""
    view = uidoc.ActiveView
    ambientes = []

    # Tenta obter todos os ambientes do projeto e filtrar os visíveis na vista ativa
    for room in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms).WhereElementIsNotElementType():
        room_name = room.get_Parameter(BuiltInParameter.ROOM_NAME).AsString()
        room_number = room.get_Parameter(BuiltInParameter.ROOM_NUMBER).AsString()
        if room_name and room_number and room.Area > 0:  # Garante que o ambiente tem um nome, número e área válida
            ambientes.append(room)

    return ambientes

# Obtém os ambientes
todos_ambientes = obter_ambientes_visiveis()

if not todos_ambientes:
    MessageBox.Show("Nenhum ambiente encontrado na vista atual.\nVerifique se os ambientes estão visíveis e corretamente criados.", "Erro")
    raise SystemExit

# Cria um dicionário com os nomes e números dos ambientes
rooms = {}
for a in todos_ambientes:
    nome = a.get_Parameter(BuiltInParameter.ROOM_NAME).AsString()
    numero = a.get_Parameter(BuiltInParameter.ROOM_NUMBER).AsString()
    if nome and numero:
        chave = "{} - {}".format(numero, nome)  # Compatível com IronPython 2
        rooms[chave] = a

# Permite ao usuário selecionar os ambientes ou aplicar para todos automaticamente
ambientes_selecionados_nomes = forms.SelectFromList.show(
    sorted(rooms.keys()),
    title="Seleção de Ambientes",
    prompt="Marque os ambientes onde deseja aplicar o revestimento:",
    multiselect=True
)

if not ambientes_selecionados_nomes:
    ambientes_selecionados_nomes = list(rooms.keys())

# Criar paredes "cebola" ao redor das existentes
with Transaction(doc, "Aplicar Revestimento") as t:
    t.Start()
    try:
        paredes_criadas = []
        for room_name in ambientes_selecionados_nomes:
            room = rooms[room_name]
            room_boundary = room.GetBoundarySegments(SpatialElementBoundaryOptions())
        
            if room_boundary:
                for segments in room_boundary:
                    for segment in segments:
                        wall_curve = segment.GetCurve()
                        deslocamento = wall_thickness / 2
                        
                        offset_direction = wall_curve.Direction.CrossProduct(XYZ.BasisZ).Normalize() * -deslocamento
                        offset_curve = Line.CreateBound(wall_curve.GetEndPoint(0) + offset_direction, wall_curve.GetEndPoint(1) + offset_direction)
                        
                        new_wall = Wall.Create(doc, offset_curve, selected_wall_type_obj.Id, room.LevelId, definir_altura_parede, 0, False, False)
                        new_wall.get_Parameter(BuiltInParameter.WALL_BASE_OFFSET).Set(0)

        t.Commit()

    except Exception as e:
        t.RollBack()
        MessageBox.Show("Erro ao aplicar o revestimento: " + str(e), "Erro")
        raise SystemExit
