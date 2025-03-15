# -- coding: utf-8 --
import clr
import math
clr.AddReference("RevitServices")
clr.AddReference("RevitNodes")
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")
clr.AddReference("System.Windows.Forms")

from pyrevit import revit, forms
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI.Selection import ObjectType
from System.Windows.Forms import Form, ListBox, Button, DialogResult, DockStyle, SelectionMode

# Obter documento do Revit
doc = revit.doc
uidoc = revit.uidoc
view = doc.ActiveView  # Vista ativa

# ---------------------- FUNÇÕES ----------------------

def selecionar_familia_tomada():
    """Pré-seleciona a família '2 TOMADAS 10A', se disponível, mas permite ao usuário escolher outra."""
    tomadas = list(FilteredElementCollector(doc)
                   .OfClass(FamilySymbol)
                   .OfCategory(BuiltInCategory.OST_ElectricalFixtures)
                   .ToElements())

    if not tomadas:
        forms.alert("Nenhuma família de tomada encontrada no modelo.", exitscript=True)
        return None

    tipos_nomes = {t.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString(): t for t in tomadas if t.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM)}

    nome_padrao = "2 TOMADAS 10A"
    opcoes = sorted(tipos_nomes.keys())

    escolha = forms.ask_for_one_item(
        opcoes,
        prompt="Escolha o tipo de tomada:",
        default=nome_padrao if nome_padrao in opcoes else None
    )

    if not escolha:
        forms.alert("Nenhuma tomada foi selecionada.", exitscript=True)
        return None

    familia_selecionada = tipos_nomes[escolha]

    t = Transaction(doc, "Ativar Família de Tomada")
    t.Start()
    if not familia_selecionada.IsActive:
        familia_selecionada.Activate()
        doc.Regenerate()
    t.Commit()

    return familia_selecionada

def obter_todos_ambientes():
    """Obtém todos os ambientes válidos do projeto."""
    return [room for room in FilteredElementCollector(doc)
            .OfCategory(BuiltInCategory.OST_Rooms)
            .WhereElementIsNotElementType()
            if room.Area > 0]

def selecionar_ambientes():
    """Exibe uma interface para seleção de um ou mais ambientes ou usa todos caso nada seja selecionado."""
    ambientes = obter_todos_ambientes()

    if not ambientes:
        forms.alert("Nenhum ambiente encontrado no projeto.", exitscript=True)
        return None

    dicionario_ambientes = {
        str(a.get_Parameter(BuiltInParameter.ROOM_NAME).AsString()): a
        for a in ambientes if a.get_Parameter(BuiltInParameter.ROOM_NAME) and
        a.get_Parameter(BuiltInParameter.ROOM_NAME).AsString()
    }

    ambientes_selecionados_nomes = forms.SelectFromList.show(
        sorted(dicionario_ambientes.keys()),
        title="Seleção de Ambientes",
        prompt="Marque os ambientes onde deseja inserir tomadas. Se não selecionar nenhum, será aplicado a todos.",
        multiselect=True
    )

    if ambientes_selecionados_nomes:
        return [dicionario_ambientes[nome] for nome in ambientes_selecionados_nomes]

    return ambientes  # Se nada for selecionado, retorna todos os ambientes

def obter_nivel_do_ambiente(ambiente):
    """Obtém o nível do ambiente."""
    nivel_id = ambiente.LevelId
    return doc.GetElement(nivel_id)  # Retorna o próprio elemento de nível

def obter_perimetro_paredes(ambiente):
    """Obtém as bordas das paredes do ambiente e direciona vetores para dentro do ambiente"""
    opt = SpatialElementBoundaryOptions()
    limites = ambiente.GetBoundarySegments(opt)
    linhas_paredes = []
    vetores_internos = []

    centro_ambiente = ambiente.Location.Point

    for limite in limites:
        for segmento in limite:
            linha = segmento.GetCurve()
            linhas_paredes.append(linha)

            vetor_direcao = (linha.GetEndPoint(1) - linha.GetEndPoint(0)).Normalize()
            vetor_perpendicular = XYZ(-vetor_direcao.Y, vetor_direcao.X, 0)

            ponto_medio = linha.Evaluate(0.0, True)
            vetor_para_centro = (centro_ambiente - ponto_medio).Normalize()

            if vetor_perpendicular.DotProduct(vetor_para_centro) < 0:
                vetor_perpendicular = -vetor_perpendicular

            vetores_internos.append(vetor_perpendicular)

    return linhas_paredes, vetores_internos

def dividir_pontos_nas_paredes(linhas, espaco_entre_tomadas, offset=0.7):
    """Divide as paredes em pontos equidistantes onde as tomadas serão inseridas, evitando cantos com offset"""
    pontos = []
    normais = []
    offset_ft = UnitUtils.ConvertToInternalUnits(offset, UnitTypeId.Meters)

    for linha in linhas:
        comprimento = linha.Length
        
        if comprimento <= 2 * offset_ft:
            continue

        qtd_tomadas = max(1, int((comprimento - 2 * offset_ft) / espaco_entre_tomadas))

        for i in range(qtd_tomadas + 1):
            parametro = offset_ft / comprimento + (float(i) / qtd_tomadas) * ((comprimento - 2 * offset_ft) / comprimento)
            ponto = linha.Evaluate(parametro, True)
            vetor_direcao = (linha.GetEndPoint(1) - linha.GetEndPoint(0)).Normalize()
            vetor_perpendicular = XYZ(-vetor_direcao.Y, vetor_direcao.X, 0)
            pontos.append(ponto)
            normais.append(vetor_perpendicular)

    return pontos, normais

def inserir_tomadas(familia, pontos, normais, nivel, altura=0.3):
    """Insere tomadas nos pontos gerados ao longo das paredes e alinha corretamente"""
    if not familia or not familia.IsActive:
        forms.alert("Família de tomada inválida. O script será encerrado.", exitscript=True)
        return

    altura_ft = UnitUtils.ConvertToInternalUnits(altura, UnitTypeId.Meters)
    t = Transaction(doc, "Inserir Tomadas")
    t.Start()
    
    for i in range(len(pontos)):
        ponto = XYZ(pontos[i].X, pontos[i].Y, altura_ft)

        tomada = doc.Create.NewFamilyInstance(ponto, familia, nivel, Structure.StructuralType.NonStructural)

        # Definir a Elevação do Nível como 0
        param_elevacao = tomada.get_Parameter(BuiltInParameter.INSTANCE_ELEVATION_PARAM)
        if param_elevacao and not param_elevacao.IsReadOnly:
            param_elevacao.Set(0)

        # Alinhar a tomada à parede
        vetor_parede = normais[i]
        referencia = XYZ(1, 0, 0)
        angulo = vetor_parede.AngleTo(referencia)

        if vetor_parede.Y < 0:
            angulo = -angulo

        angulo -= math.pi / 2

        eixo_rotacao = Line.CreateBound(ponto, ponto + XYZ(0, 0, 1))
        ElementTransformUtils.RotateElement(doc, tomada.Id, eixo_rotacao, angulo)

    t.Commit()

# ---------------------- EXECUÇÃO DO SCRIPT ----------------------

if not doc:
    forms.alert("Nenhum documento ativo encontrado. Abra um projeto no Revit antes de executar o script.", exitscript=True)
else:
    familia_tomada = selecionar_familia_tomada()
    if familia_tomada:
        ambientes = selecionar_ambientes()
        espaco_entre_tomadas = float(forms.ask_for_string(
            title="Distância entre Tomadas",
            prompt="Digite a distância entre as tomadas (em metros):"
        ))
        espaco_entre_tomadas_ft = UnitUtils.ConvertToInternalUnits(espaco_entre_tomadas, UnitTypeId.Meters)

        for ambiente in ambientes:
            nivel = obter_nivel_do_ambiente(ambiente)
            linhas_paredes, vetores_internos = obter_perimetro_paredes(ambiente)
            pontos, normais = dividir_pontos_nas_paredes(linhas_paredes, espaco_entre_tomadas_ft)
            inserir_tomadas(familia_tomada, pontos, normais, nivel)
