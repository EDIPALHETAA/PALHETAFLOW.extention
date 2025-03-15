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
uiapp = __revit__
app = uiapp.Application

if doc is None:
    MessageBox.Show("Nenhum documento ativo encontrado. Abra um projeto no Revit antes de executar o script.", "Erro")
    raise SystemExit

# Obtém os tipos de parede disponíveis no projeto
def obter_tipos_de_parede():
    return list(FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Walls).OfClass(WallType).WhereElementIsElementType())

tipos_de_parede = obter_tipos_de_parede()
if not tipos_de_parede:
    MessageBox.Show("Nenhum tipo de parede encontrado no projeto.", "Erro")
    raise SystemExit

wall_type_dict = {tipo.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString() or tipo.Name: tipo for tipo in tipos_de_parede}

selected_wall_type = forms.ask_for_one_item(
    items=sorted(wall_type_dict.keys()),
    default='PORCELANATO ELIZABETH BRANCO 24 X 35 CM',
    title="Seleção de Tipo de Parede",
    prompt="Escolha o tipo de parede a ser aplicada:"
)

if not selected_wall_type:
    MessageBox.Show("Nenhum tipo de parede selecionado.", "Erro")
    raise SystemExit

selected_wall_type_obj = wall_type_dict[selected_wall_type]

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

# Pergunta ao usuário a altura da parede
altura_parede_str = forms.ask_for_string(
    default='2.15',
    title='Definir Altura da Parede',
    prompt='Informe a altura da parede (em metros):'
)

if not altura_parede_str:
    MessageBox.Show('Nenhuma altura definida. O processo foi cancelado.', 'Erro')
    raise SystemExit

try:
    definir_altura_parede = UnitUtils.ConvertToInternalUnits(float(altura_parede_str), UnitTypeId.Meters)
except ValueError:
    MessageBox.Show('Valor inválido para a altura da parede. O processo foi cancelado.', 'Erro')
    raise SystemExit

paredes_novas = []

# Inicia a transação para criar as paredes
t = Transaction(doc, "Criar Paredes Novas")
t.Start()

try:
    for room_chave in ambientes_selecionados_nomes:
        room = rooms[room_chave]
        room_boundary = room.GetBoundarySegments(SpatialElementBoundaryOptions())

        if room_boundary:
            for segments in room_boundary:
                for segment in segments:
                    wall_curve = segment.GetCurve()
                    if not wall_curve:
                        continue
                    
                    wall_thickness = selected_wall_type_obj.get_Parameter(BuiltInParameter.WALL_ATTR_WIDTH_PARAM).AsDouble()
                    deslocamento = wall_thickness / 2
                    
                    # Calcula o deslocamento para a posição correta da parede
                    offset_direction = wall_curve.Direction.CrossProduct(XYZ.BasisZ).Normalize() * -deslocamento
                    offset_curve = Line.CreateBound(wall_curve.GetEndPoint(0) + offset_direction, wall_curve.GetEndPoint(1) + offset_direction)
                    
                    # Cria a parede
                    new_wall = Wall.Create(doc, offset_curve, selected_wall_type_obj.Id, room.LevelId, definir_altura_parede, 0, False, False)
                    new_wall.get_Parameter(BuiltInParameter.WALL_BASE_OFFSET).Set(0)
                    paredes_novas.append(new_wall)

    t.Commit()

except Exception as e:
    t.RollBack()
    MessageBox.Show("Erro ao criar paredes novas: " + str(e), "Erro")
    raise SystemExit
