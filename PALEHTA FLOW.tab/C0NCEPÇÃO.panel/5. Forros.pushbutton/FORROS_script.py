# -*- coding: utf-8 -*-
from Autodesk.Revit.DB import (
    FilteredElementCollector,
    Transaction,
    BuiltInCategory,
    BuiltInParameter,
    Ceiling,
    CeilingType,
    Level,
    XYZ,
    CurveLoop,
    SpatialElementBoundaryOptions
)
from pyrevit import revit, forms

# Obtém o documento ativo e a vista ativa no Revit
doc = revit.doc
vista_atual = doc.ActiveView

# Nome do forro padrão
FORRO_PADRAO_NOME = "FORRO DE GESSO"

# Função para obter todos os tipos de forro disponíveis no projeto
def obter_tipos_de_forro():
    return list(FilteredElementCollector(doc)
                .OfClass(CeilingType)
                .WhereElementIsElementType())

# Obtém a lista de tipos de forro
tipos_de_forro = obter_tipos_de_forro()
if not tipos_de_forro:
    forms.alert("Nenhum tipo de forro foi encontrado no projeto.", exitscript=True)

# Criamos um dicionário para associar os nomes aos tipos de forro
mapa_tipos_forro = {}
tipo_padrao = None  # Variável para armazenar o tipo de forro padrão

for tipo in tipos_de_forro:
    nome_forro = tipo.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
    if not nome_forro:
        nome_forro = tipo.Name  # Caso não tenha, usa o nome padrão do elemento
    
    mapa_tipos_forro[nome_forro] = tipo

    # Se o forro padrão for encontrado, armazenamos ele
    if nome_forro == FORRO_PADRAO_NOME:
        tipo_padrao = nome_forro

# Se o forro padrão não for encontrado, usa o primeiro da lista
tipo_padrao = tipo_padrao if tipo_padrao else list(mapa_tipos_forro.keys())[0]

# Exibir uma lista com os nomes dos tipos de forro para o usuário escolher
tipo_escolhido_nome = forms.ask_for_one_item(
    items=list(mapa_tipos_forro.keys()),  # Exibe os nomes dos forros
    default=tipo_padrao,  # Define o padrão
    prompt="Selecione o tipo de forro desejado:",
    title="Seleção de Tipo de Forro"
)

# Se o usuário cancelar, interromper o script
if not tipo_escolhido_nome:
    forms.alert("Nenhum tipo de forro selecionado.", exitscript=True)

# Obtém o tipo de forro correspondente ao nome escolhido
tipo_escolhido = mapa_tipos_forro[tipo_escolhido_nome]

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
    title="Seleção de Ambientes",
    prompt="Marque os ambientes onde deseja aplicar o forro:",
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

# Função para criar forros nos ambientes detectados
def criar_forros_nos_ambientes():
    t = Transaction(doc, "Criação de forros nos ambientes")
    t.Start()
    
    for ambiente in dicionario_ambientes_selecionados.values():
        try:
            # Obtém o nível do ambiente
            nivel = doc.GetElement(ambiente.LevelId)
            
            # Obtém as bordas do ambiente (linhas de contorno)
            limites = ambiente.GetBoundarySegments(boundary_options)
            if not limites:
                continue
            
            # Cria um CurveLoop para definir a área do forro
            curva_loop = CurveLoop()
            for segmento in limites[0]:  # Usa o primeiro conjunto de limites
                curva_loop.Append(segmento.GetCurve())

            # Criar o forro dentro do ambiente
            novo_forro = Ceiling.Create(doc, [curva_loop], tipo_escolhido.Id, nivel.Id)
        
        except Exception as e:
            print("Erro ao criar forro no ambiente {}: {}".format(ambiente.Id, e))
    
    t.Commit()

# Criar os forros nos ambientes da vista atual
criar_forros_nos_ambientes()
