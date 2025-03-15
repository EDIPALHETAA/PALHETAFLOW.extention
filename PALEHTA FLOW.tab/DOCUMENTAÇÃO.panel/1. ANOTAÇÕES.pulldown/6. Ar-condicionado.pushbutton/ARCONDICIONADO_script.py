# -*- coding: utf-8 -*-
# Compatível com IronPython 2 para PyRevit

# Importações necessárias
import clr
clr.AddReference("RevitAPI")
clr.AddReference("RevitServices")
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, BuiltInParameter
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager
from pyrevit import forms, revit
import math

# Obter documento do Revit
doc = revit.doc
uidoc = revit.uidoc
view = doc.ActiveView  # Vista ativa

# Função para converter a área de pés² para m²
def converter_para_m2(area_ft2):
    return area_ft2 * 0.092903  # 1 ft² = 0.092903 m²

# Função para calcular a capacidade total necessária (1000 BTUs por m²)
def calcular_capacidade_total(area_m2):
    return area_m2 * 1000  # 1000 BTUs por metro quadrado

# Função para otimizar a quantidade e capacidade das máquinas de forma proporcional
def otimizar_maquinas_proporcionais(capacidade_total, area_m2):
    # Capacidades disponíveis no template, priorizando as maiores permitidas proporcionalmente
    if area_m2 <= 12:
        capacidades_disponiveis = [9000]
    elif area_m2 <= 24:
        capacidades_disponiveis = [12000, 9000]
    elif area_m2 <= 36:
        capacidades_disponiveis = [18000, 12000, 9000]
    elif area_m2 <= 50:
        capacidades_disponiveis = [24000, 18000, 12000, 9000]
    elif area_m2 <= 70:
        capacidades_disponiveis = [30000, 24000, 18000, 12000, 9000]
    elif area_m2 <= 90:
        capacidades_disponiveis = [36000, 30000, 24000, 18000, 12000, 9000]
    elif area_m2 <= 150:
        capacidades_disponiveis = [48000, 36000, 30000, 24000, 18000, 12000, 9000]
    else:
        capacidades_disponiveis = [55000, 48000, 36000, 30000, 24000, 18000, 12000, 9000]

    # Otimização: selecionar a menor quantidade possível de máquinas
    for capacidade in capacidades_disponiveis:
        quantidade = math.ceil(capacidade_total / capacidade)
        if quantidade * capacidade >= capacidade_total:
            return quantidade, capacidade

    # Caso exceda a maior capacidade proporcional disponível
    capacidade_maior = capacidades_disponiveis[0]
    quantidade = math.ceil(capacidade_total / capacidade_maior)
    return quantidade, capacidade_maior

# Função para obter o valor seguro do parâmetro
def obter_valor_parametro(elemento, parametro_nome, valor_padrao="Sem Nome"):
    parametro = elemento.get_Parameter(parametro_nome)
    if parametro:
        valor = parametro.AsString()
        if valor:
            return valor
    return valor_padrao

# Função para obter os ambientes visíveis na vista ativa
def obter_ambientes_visiveis():
    """Obtém os ambientes (Rooms) visíveis na vista ativa do usuário no Revit."""
    ambientes = []
    for room in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms).WhereElementIsNotElementType():
        room_name = obter_valor_parametro(room, BuiltInParameter.ROOM_NAME)
        room_number = obter_valor_parametro(room, BuiltInParameter.ROOM_NUMBER, "Sem Número")
        if room_name and room_number and room.Area > 0:  # Garante que o ambiente tem um nome, número e área válida
            ambientes.append(room)
    return ambientes

# Função principal para processar os ambientes selecionados
def processar_ambientes():
    # Obtém os ambientes
    todos_ambientes = obter_ambientes_visiveis()

    if not todos_ambientes:
        forms.alert("Nenhum ambiente encontrado na vista atual.\nVerifique se os ambientes estão visíveis e corretamente criados.", title="Aviso", warn_icon=True)
        return

    # Cria um dicionário com os nomes e números dos ambientes
    rooms = {}
    for a in todos_ambientes:
        nome = obter_valor_parametro(a, BuiltInParameter.ROOM_NAME)
        numero = obter_valor_parametro(a, BuiltInParameter.ROOM_NUMBER, "Sem Número")
        chave = "{} - {}".format(numero, nome)  # Compatível com IronPython 2
        rooms[chave] = a

    # Permite ao usuário selecionar os ambientes
    ambientes_selecionados_nomes = forms.SelectFromList.show(
        sorted(rooms.keys()),
        title="Seleção de Ambientes",
        prompt="Marque os ambientes que deseja analisar:",
        multiselect=True
    )

    if not ambientes_selecionados_nomes:
        forms.alert("Nenhum ambiente selecionado. Operação cancelada.", title="Aviso", warn_icon=True)
        return

    # Processa cada ambiente selecionado e exibe em formulário de aviso
    for ambiente_nome in ambientes_selecionados_nomes:
        ambiente = rooms[ambiente_nome]
        area_ft2 = ambiente.Area
        area_m2 = converter_para_m2(area_ft2)
        capacidade_total = calcular_capacidade_total(area_m2)
        quantidade, capacidade_maquina = otimizar_maquinas_proporcionais(capacidade_total, area_m2)

        mensagem = (
            "Ambiente: {}\n"
            "Área: {:.2f} m²\n"
            "Capacidade total necessária: {:,} BTUs\n"
            "Quantidade de máquinas necessárias: {}\n"
            "Capacidade de cada máquina: {:,} BTUs"
        ).format(
            obter_valor_parametro(ambiente, BuiltInParameter.ROOM_NAME),
            area_m2,
            int(capacidade_total),
            quantidade,
            capacidade_maquina
        )

        forms.alert(mensagem, title="Informações do Ambiente", warn_icon=False)

# Executar o script
if doc is not None:
    processar_ambientes()
else:
    forms.alert("Nenhum documento ativo no Revit.", title="Erro", warn_icon=True)
