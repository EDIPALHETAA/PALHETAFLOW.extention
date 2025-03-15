# -*- coding: utf-8 -*-

import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitServices')

from Autodesk.Revit.DB import (
    FilteredElementCollector, BuiltInCategory, ElementType, BuiltInParameter, 
    Transaction, XYZ, Line, Structure, Level
)
from Autodesk.Revit.UI.Selection import ObjectType
from RevitServices.Persistence import DocumentManager
from pyrevit import forms

# Obtém o documento ativo
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document  

# Obtém todos os tipos de vigas disponíveis no projeto
quadros_estruturais = FilteredElementCollector(doc)\
    .OfCategory(BuiltInCategory.OST_StructuralFraming)\
    .WhereElementIsElementType()\
    .ToElements()

# Verifica se há tipos disponíveis
if not quadros_estruturais:
    forms.alert("Nenhum tipo de viga encontrado no projeto.", exitscript=True)

# Criando um dicionário com os nomes dos tipos de viga
tipos_dict = {
    q.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString(): q for q in quadros_estruturais
}

# Ordenando os nomes das vigas para exibição
tipos_nomes = sorted(tipos_dict.keys())

# Definir uma opção padrão
default_tipo = tipos_nomes[0] if tipos_nomes else None

# Criando a interface de seleção da viga
tipo_escolhido_nome = forms.ask_for_one_item(
    tipos_nomes,
    default=default_tipo,
    prompt="Selecione um Tipo de Viga",
    title="Escolha o Tipo"
)

# Verifica se o usuário fez uma seleção
if not tipo_escolhido_nome:
    forms.alert("Nenhuma viga foi selecionada.", exitscript=True)

# Obtém o tipo de viga escolhido pelo usuário
tipo_escolhido = tipos_dict[tipo_escolhido_nome]

# Obtém os elementos selecionados
selecionados = uidoc.Selection.GetElementIds()
if not selecionados:
    forms.alert("Nenhuma parede selecionada. Por favor, selecione as paredes antes de rodar o script.", exitscript=True)

paredes = [doc.GetElement(eid) for eid in selecionados if doc.GetElement(eid).Category.Id.IntegerValue == int(BuiltInCategory.OST_Walls)]
if not paredes:
    forms.alert("Os elementos selecionados não são paredes válidas.", exitscript=True)

# Solicita a altura personalizada do usuário (em metros, convertida para pés)
altura_usuario = forms.ask_for_string(
    prompt="Digite a altura de deslocamento da viga em metros (em relação à base da parede):",
    title="Definir Altura da Viga",
    default="0.0"
)

# Converte o valor para número (se for inválido, assume 0)
try:
    altura_deslocamento = float(altura_usuario) if altura_usuario else 0.0
except ValueError:
    altura_deslocamento = 0.0

# Convertendo altura para unidade interna do Revit (metros para pés)
altura_deslocamento = altura_deslocamento * 3.28084

# Criando as vigas nas paredes selecionadas
t = Transaction(doc, "Adicionar Vigas nas Paredes Selecionadas")
t.Start()

try:
    for parede in paredes:
        # Obtém o nível da parede
        nivel_parede = doc.GetElement(parede.LevelId)
        if not isinstance(nivel_parede, Level):
            continue

        # Obtém a elevação do nível da base da parede
        base_elevation = nivel_parede.Elevation

        # Obtém a linha central da parede
        location_curve = parede.Location.Curve
        if not location_curve:
            continue

        # Obtém os pontos de início e fim da parede
        start = location_curve.GetEndPoint(0)
        end = location_curve.GetEndPoint(1)

        # Calcula a nova altura da viga baseada no nível da base da parede
        nova_altura = base_elevation + altura_deslocamento

        # Criando a linha para a viga com deslocamento aplicado
        start_offset = XYZ(start.X, start.Y, nova_altura)
        end_offset = XYZ(end.X, end.Y, nova_altura)
        linha_viga = Line.CreateBound(start_offset, end_offset)

        # Criando a viga com StructuralType.Beam e associando ao mesmo nível da parede
        viga = doc.Create.NewFamilyInstance(
            linha_viga, tipo_escolhido, nivel_parede,
            Structure.StructuralType.Beam
        )

except Exception as e:
    forms.alert("Ocorreu um erro ao criar as vigas:\n{}".format(str(e)))

t.Commit()
