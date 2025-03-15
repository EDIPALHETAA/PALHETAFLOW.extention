# -*- coding: utf-8 -*-
__title__ = "Colocar Tomada no Lado da Abertura da Porta (270° Rotacao)"
__author__ = "Edi Carlos"
__doc__ = "Seleciona uma porta e insere uma tomada na face da parede para onde a porta abre, rotacionada em 270°."

import clr
clr.AddReference("RevitServices")
from RevitServices.Persistence import DocumentManager

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *

from pyrevit import forms
import math

# Obter documento do Revit
from pyrevit import revit

doc = revit.doc
uidoc = revit.uidoc
view = doc.ActiveView  # Vista ativa

# Obtém a seleção do usuário
selecionados = uidoc.Selection.GetElementIds()

# Verifica se há uma única porta selecionada
if not selecionados:
    forms.alert("Nenhuma porta selecionada. Selecione uma porta e execute novamente.", exitscript=True)

porta_selecionada = None
for elem_id in selecionados:
    elemento = doc.GetElement(elem_id)
    if elemento and elemento.Category and elemento.Category.Id.IntegerValue == int(BuiltInCategory.OST_Doors):
        porta_selecionada = elemento
        break

if not porta_selecionada:
    forms.alert("O elemento selecionado não é uma porta válida.", exitscript=True)

# Obtém todos os tipos de tomadas elétricas do projeto
colecao_tomadas = FilteredElementCollector(doc)\
    .OfCategory(BuiltInCategory.OST_ElectricalFixtures)\
    .WhereElementIsElementType()\
    .ToElements()

if not colecao_tomadas:
    forms.alert("Nenhuma tomada encontrada no projeto.", exitscript=True)

# Criando um dicionário {Nome: Elemento} para facilitar a seleção
tipos_nomes = {
    t.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString(): t 
    for t in colecao_tomadas 
    if t.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM)
}

nome_padrao = "1 TOMADA 20A + INTERRUPTOR"
opcoes = sorted(tipos_nomes.keys())

# Exibe a interface de seleção com forms.ask_for_one_item()
escolha = forms.ask_for_one_item(
    opcoes,
    prompt="Escolha o tipo de tomada:",
    default=nome_padrao if nome_padrao in opcoes else None
)

if not escolha:
    forms.alert("Nenhuma tomada foi selecionada.", exitscript=True)

tipo_selecionado = tipos_nomes.get(escolha)
if not tipo_selecionado:
    forms.alert("Erro ao obter a tomada selecionada.", exitscript=True)

# Solicita o deslocamento desejado do usuário
deslocamento_str = forms.ask_for_string(
    prompt="Informe o deslocamento da tomada em metros:",
    default="0.2"
)

# Verifica se o usuário cancelou ou deixou o campo vazio
if deslocamento_str is None or deslocamento_str.strip() == "":
    forms.alert("Você precisa definir um valor de deslocamento.", exitscript=True)

# Converte o deslocamento para float
try:
    deslocamento_m = float(deslocamento_str)
except ValueError:
    forms.alert("Entrada inválida. Informe um número válido para o deslocamento.", exitscript=True)

# Obtém a largura da porta
param_largura = porta_selecionada.Symbol.get_Parameter(BuiltInParameter.DOOR_WIDTH)
if not param_largura or not param_largura.HasValue:
    forms.alert("A largura da porta não pôde ser obtida.", exitscript=True)

largura_porta_m = param_largura.AsDouble() * 0.3048

# Ajusta o deslocamento considerando a largura da porta
deslocamento_m = (largura_porta_m / 2) + deslocamento_m
deslocamento_pes = deslocamento_m * 3.28084

# Obtém a localização da porta
ponto_porta = porta_selecionada.Location.Point
if not ponto_porta:
    forms.alert("A localização da porta não pôde ser determinada.", exitscript=True)

normal_porta = porta_selecionada.FacingOrientation
if not normal_porta:
    forms.alert("A orientação da porta não pôde ser determinada.", exitscript=True)

direcao_abertura = porta_selecionada.HandOrientation
if not direcao_abertura:
    forms.alert("A direção de abertura da porta não pôde ser determinada.", exitscript=True)

# Obtém o host da porta (parede)
hospedeiro = porta_selecionada.Host
if not hospedeiro or not isinstance(hospedeiro, Wall):
    forms.alert("A porta não está hospedada em uma parede válida.", exitscript=True)

espessura_parede = hospedeiro.Width if hospedeiro else 0
espessura_parede_m = espessura_parede * 0.3048

nova_posicao = XYZ(
    ponto_porta.X + (direcao_abertura.X * (espessura_parede_m / 2 + deslocamento_pes)),
    ponto_porta.Y + (direcao_abertura.Y * (espessura_parede_m / 2 + deslocamento_pes)),
    ponto_porta.Z
)

ponto_de_rotacao = nova_posicao
angulo_porta = math.atan2(normal_porta.Y, normal_porta.X)
angulo_rotacao_final = angulo_porta + math.radians(270)

eixo_rotacao = Line.CreateBound(ponto_de_rotacao, ponto_de_rotacao + XYZ(0, 0, 1))

def mover_tomada(elemento, normal, deslocamento):
    if not elemento:
        forms.alert("Erro: elemento da tomada não foi criado.", exitscript=True)
    vetor_deslocamento = XYZ(normal.X * deslocamento, normal.Y * deslocamento, 0)
    ElementTransformUtils.MoveElement(doc, elemento.Id, vetor_deslocamento)

try:
    t = Transaction(doc, "Inserir e Alinhar Tomada")
    t.Start()
    
    nova_tomada = doc.Create.NewFamilyInstance(nova_posicao, tipo_selecionado, Structure.StructuralType.NonStructural)
    
    if not nova_tomada:
        t.RollBack()
        forms.alert("Erro ao criar a tomada.", exitscript=True)
    
    ElementTransformUtils.RotateElement(doc, nova_tomada.Id, eixo_rotacao, angulo_rotacao_final)
    mover_tomada(nova_tomada, normal_porta, espessura_parede / 2)

    t.Commit()
except Exception as e:
    t.RollBack()
    forms.alert("Erro durante a criação da tomada: {}".format(str(e)), exitscript=True)
