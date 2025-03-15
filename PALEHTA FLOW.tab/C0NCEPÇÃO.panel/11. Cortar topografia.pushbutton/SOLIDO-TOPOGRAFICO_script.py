# -*- coding: utf-8 -*-
import clr
clr.AddReference('RevitServices')
clr.AddReference('RevitAPI')
clr.AddReference('RevitNodes')

from RevitServices.Persistence import DocumentManager
from Autodesk.Revit.DB import (
    FilteredElementCollector, BuiltInCategory, ElementCategoryFilter, 
    JoinGeometryUtils, Transaction
)

# Obtém o documento ativo corretamente
uiapp = __revit__  
uidoc = uiapp.ActiveUIDocument
doc = uidoc.Document  

# Verifica se o documento está carregado corretamente
if doc is None:
    raise Exception("Erro: Nenhum documento Revit ativo encontrado.")

# Definição de filtros para elementos estruturais e topografia
filtros_elementos = {
    "Paredes": BuiltInCategory.OST_Walls,
    "Pilares": BuiltInCategory.OST_StructuralColumns,
    "Vigas/Quadros": BuiltInCategory.OST_StructuralFraming,
    "Fundações": BuiltInCategory.OST_StructuralFoundation
}

# Buscar TopoSurface (Revit antigo) e TopoSolid (Revit 2024+)
topo_categories = [BuiltInCategory.OST_Topography, BuiltInCategory.OST_Toposolid]
filtro_topografia = [ElementCategoryFilter(cat) for cat in topo_categories]

# Coleta os elementos estruturais do modelo
elementos_modelo = {}
for nome, categoria in filtros_elementos.items():
    elementos_modelo[nome] = list(
        FilteredElementCollector(doc).WherePasses(ElementCategoryFilter(categoria)).WhereElementIsNotElementType().ToElements()
    )

# Coleta os sólidos topográficos
topografias = []
for filtro in filtro_topografia:
    topografias.extend(
        FilteredElementCollector(doc).WherePasses(filtro).WhereElementIsNotElementType().ToElements()
    )

# Verifica se há um sólido topográfico no modelo
if not topografias:
    raise Exception("Nenhum sólido topográfico encontrado no modelo.")

topografia = topografias[0]  # Seleciona o primeiro sólido topográfico encontrado

# Inicia a transação
t = Transaction(doc, "Unir Elementos Estruturais com Topografia")
t.Start()

try:
    def unir_elementos(elementos, topo):
        """Tenta unir cada elemento da lista com o sólido topográfico."""
        for elem in elementos:
            try:
                JoinGeometryUtils.JoinGeometry(doc, topo, elem)
            except:
                pass  # Ignora erros individuais sem interromper o processo

    # Aplica a união de todos os elementos estruturais com a topografia
    for elementos in elementos_modelo.values():
        unir_elementos(elementos, topografia)

    # Finaliza a transação corretamente
    t.Commit()

except:
    t.RollBack()  # Desfaz a transação em caso de erro
