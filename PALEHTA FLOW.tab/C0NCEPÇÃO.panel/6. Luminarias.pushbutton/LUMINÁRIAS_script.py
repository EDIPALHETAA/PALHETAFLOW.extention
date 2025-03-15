# -*- coding: utf-8 -*-
import clr
clr.AddReference("RevitServices")
clr.AddReference("RevitAPI")
clr.AddReference("RevitNodes")

from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, XYZ, Transaction, Structure, Options, BuiltInParameter
from pyrevit import revit, forms, UI
import math

# Obter documento ativo do Revit
doc = revit.doc
uidoc = revit.uidoc

# Perguntar ao usuário se deseja selecionar forros ou aplicar em todos
opcao = forms.alert("Você deseja selecionar os forros manualmente ou aplicar em todos?",
                    options=["Selecionar Forros", "Aplicar em Todos"])

# Se o usuário escolheu "Selecionar Forros", permitir seleção manual
if opcao == "Selecionar Forros":
    try:
        forros_selecionados = uidoc.Selection.PickObjects(UI.Selection.ObjectType.Element, "Selecione os forros onde deseja inserir luminárias.")
        forros = [doc.GetElement(ref.ElementId) for ref in forros_selecionados]
    except:
        raise SystemExit
else:
    # Se escolher "Aplicar em Todos", pegar todos os forros do projeto
    forros = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Ceilings).WhereElementIsNotElementType().ToElements()

if not forros:
    raise Exception("Nenhum forro encontrado!")

# Obter tipos de luminária disponíveis no projeto
luminaria_familias = [f for f in FilteredElementCollector(doc)
                      .OfCategory(BuiltInCategory.OST_LightingFixtures)
                      .WhereElementIsElementType()]

if not luminaria_familias:
    raise Exception("Nenhuma luminária encontrada no projeto!")

# Selecionar o tipo de luminária
tipos_nomes = {f.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString(): f for f in luminaria_familias}
default_selection = "PLAFON STELLA QUADRADO EMBUTIDO  30X30CM"
escolha = forms.ask_for_one_item(sorted(tipos_nomes.keys()), default=default_selection, prompt="Escolha o tipo de luminária:")
if not escolha:
    raise Exception("Nenhuma luminária selecionada!")

tipo_luminaria = tipos_nomes[escolha]

# Definições padrão
lux_padrao = 400  # Iluminação necessária (lux)
fluxo_luminoso_luminaria = 2400  # Lumens por luminária

# Criar transação
with Transaction(doc, "Inserir Luminárias") as t:
    t.Start()
    
    for forro in forros:
        # Criar uma instância de Options para acessar a geometria
        opt = Options()
        forro_geom = forro.get_Geometry(opt)

        # Verificar se a geometria foi encontrada
        if not forro_geom:
            continue

        # Obter os limites do forro
        elemento_bbox = forro_geom.GetBoundingBox()
        if not elemento_bbox:
            continue

        min_point = elemento_bbox.Min
        max_point = elemento_bbox.Max

        # Obter a área do forro e converter de pés² para m²
        param_area = forro.LookupParameter(u"Área")
        area_forro = param_area.AsDouble() * 0.092903 if param_area and param_area.HasValue else 0

        # Obter a altura do forro e converter de pés para metros
        param_altura_deslocamento = forro.LookupParameter(u"Altura do deslocamento do nível")
        altura_forro = param_altura_deslocamento.AsDouble() * 0.3048 if param_altura_deslocamento and param_altura_deslocamento.HasValue else 0

        # Obter a largura e comprimento do forro e converter de pés para metros
        largura = (max_point.X - min_point.X) * 0.3048  
        comprimento = (max_point.Y - min_point.Y) * 0.3048  

        # Evitar divisões por zero
        if largura <= 0 or comprimento <= 0:
            print("⚠️ Forro ID {} ignorado: largura ou comprimento inválido.".format(forro.Id.IntegerValue))
            continue

        # Obter o nível do forro
        param_nivel = forro.LookupParameter(u"Nível")
        nivel_forro_elemento = doc.GetElement(param_nivel.AsElementId()) if param_nivel and param_nivel.HasValue else None

        if not nivel_forro_elemento:
            continue

        # Calcular a quantidade de luminárias necessária
        fluxo_necessario = area_forro * lux_padrao
        qtd_luminarias = max(1, round(fluxo_necessario / fluxo_luminoso_luminaria))

        # Determinar número de colunas e linhas automaticamente
        num_colunas = max(1, int(math.sqrt(qtd_luminarias * (largura / comprimento))))
        num_linhas = max(1, int(math.ceil(qtd_luminarias / num_colunas)))

        # Calcular espaçamentos
        espacamento_x = largura / (num_colunas + 1)
        espacamento_y = comprimento / (num_linhas + 1)

        # Inserir as luminárias no forro
        for i in range(1, num_linhas + 1):
            for j in range(1, num_colunas + 1):
                x = min_point.X + (espacamento_x * j / 0.3048)  # Converter de metros para pés
                y = min_point.Y + (espacamento_y * i / 0.3048)  # Converter de metros para pés
                z = altura_forro / 0.3048  # Converter para pés
                posicao = XYZ(x, y, z)

                try:
                    luminaria_instancia = doc.Create.NewFamilyInstance(posicao, tipo_luminaria, nivel_forro_elemento, Structure.StructuralType.NonStructural)
                    
                    # Ajustar a elevação da luminária para coincidir com a altura do deslocamento do nível do forro
                    param_elevacao = luminaria_instancia.LookupParameter("Elevação do nível")
                    if param_elevacao and not param_elevacao.IsReadOnly:
                        param_elevacao.Set(altura_forro / 0.3048)  # Converter para pés

                    # Definir valores fixos para "Elevação do Ponto" e "Altura Rebaixo"
                    param_elevacao_ponto = luminaria_instancia.LookupParameter("Elevação do Ponto")
                    if param_elevacao_ponto and not param_elevacao_ponto.IsReadOnly:
                        param_elevacao_ponto.Set(0.1 / 0.3048)  # Converter para pés

                    param_altura_rebaixo = luminaria_instancia.LookupParameter("Altura Rebaixo")
                    if param_altura_rebaixo and not param_altura_rebaixo.IsReadOnly:
                        param_altura_rebaixo.Set(0)
                except:
                    pass
    
    t.Commit()
