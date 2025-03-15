# -*- coding: utf-8 -*-
from Autodesk.Revit.DB import (
    FilteredElementCollector,
    Transaction,
    BuiltInCategory,
    BuiltInParameter,
    Floor,
    FloorType,
    Level,
    XYZ,
    CurveLoop,
    SpatialElementBoundaryOptions
)
from pyrevit import revit, forms

# Obtém o documento ativo e a vista ativa no Revit
doc = revit.doc
vista_atual = doc.ActiveView

# Nome do piso padrão
PISO_PADRAO_NOME = "PROCELANATO ELIZABETH CARRARA CINZA AC 74X74CM"

# Função para obter todos os tipos de piso disponíveis no projeto
def obter_tipos_de_piso():
    return list(FilteredElementCollector(doc)
                .OfClass(FloorType)
                .WhereElementIsElementType())

# Obtém a lista de tipos de piso
tipos_de_piso = obter_tipos_de_piso()
if not tipos_de_piso:
    forms.alert("Nenhum tipo de piso encontrado no projeto.", exitscript=True)

# Criamos um dicionário para associar os nomes aos tipos de piso
mapa_tipos_piso = {}
tipo_padrao = None  # Variável para armazenar o tipo de piso padrão

for tipo in tipos_de_piso:
    nome_piso = tipo.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
    if not nome_piso:
        nome_piso = tipo.Name  # Caso não tenha, usa o nome padrão do elemento
    
    mapa_tipos_piso[nome_piso] = tipo

    # Se o piso padrão for encontrado, armazenamos ele
    if nome_piso == PISO_PADRAO_NOME:
        tipo_padrao = nome_piso

# Se o piso padrão não for encontrado, usa o primeiro da lista
tipo_padrao = tipo_padrao if tipo_padrao else list(mapa_tipos_piso.keys())[0]

# Exibir uma lista com os nomes dos tipos de piso para o usuário escolher
tipo_escolhido_nome = forms.ask_for_one_item(
    items=list(mapa_tipos_piso.keys()),  # Exibe os nomes dos pisos
    default=tipo_padrao,  # Define o padrão
    prompt="ESCOLHA O TIPO DE PISO:",
    title="SELEÇÃO DE TIPO DE PISO"
)

# Se o usuário cancelar, interromper o script
if not tipo_escolhido_nome:
    forms.alert("Nenhum tipo de piso selecionado.", exitscript=True)

# Obtém o tipo de piso correspondente ao nome escolhido
tipo_escolhido = mapa_tipos_piso[tipo_escolhido_nome]

# Obtém os ambientes (Rooms) da vista atual
ambientes = [room for room in FilteredElementCollector(doc)
                 .OfCategory(BuiltInCategory.OST_Rooms)
                 .WhereElementIsNotElementType()
                 if room.Area > 0]  # Apenas ambientes colocados

# Criar um dicionário onde a chave inclui o nome e o número do ambiente
dicionario_ambientes = {}
for ambiente in ambientes:
    nome = ambiente.get_Parameter(BuiltInParameter.ROOM_NAME).AsString()
    numero = ambiente.get_Parameter(BuiltInParameter.ROOM_NUMBER).AsString()
    if nome and numero:
        chave = "{} - {}".format(numero, nome)  # Compatível com IronPython 2
        dicionario_ambientes[chave] = ambiente

# Exibir interface de seleção de ambientes com nome e número
ambientes_selecionados_nomes = forms.SelectFromList.show(
    sorted(dicionario_ambientes.keys()),
    title="SELEÇÃO DE AMBIENTE",
    prompt="MARQUE OS AMBIENTES ONDE DESEJA APLICAR OS PISOS:",
    multiselect=True
)

# Se o usuário não selecionar nada, aplicamos a todos os ambientes
dicionario_ambientes_selecionados = {}
if ambientes_selecionados_nomes:
    for chave in ambientes_selecionados_nomes:
        if chave in dicionario_ambientes:
            dicionario_ambientes_selecionados[chave] = dicionario_ambientes[chave]
else:
    dicionario_ambientes_selecionados = dicionario_ambientes

# Configuração para obter os limites dos ambientes
boundary_options = SpatialElementBoundaryOptions()

# Função para criar pisos nos ambientes detectados
def criar_pisos_nos_ambientes():
    t = Transaction(doc, "Criação de pisos nos ambientes")
    t.Start()
    
    for ambiente in dicionario_ambientes_selecionados.values():
        try:
            # Obtém o nível do ambiente
            nivel = doc.GetElement(ambiente.LevelId)
            
            # Obtém as bordas do ambiente (linhas de contorno)
            limites = ambiente.GetBoundarySegments(boundary_options)
            if not limites:
                continue
            
            # Cria um CurveLoop para definir a área do piso
            curva_loop = CurveLoop()
            for segmento in limites[0]:  # Usa o primeiro conjunto de limites
                curva_loop.Append(segmento.GetCurve())

            # Cria o piso dentro do ambiente
            novo_piso = Floor.Create(doc, [curva_loop], tipo_escolhido.Id, nivel.Id)
        
        except Exception as e:
            print("Erro ao criar piso no ambiente {}: {}".format(ambiente.Id, e))
    
    t.Commit()

# Criar os pisos nos ambientes da vista atual
criar_pisos_nos_ambientes()
