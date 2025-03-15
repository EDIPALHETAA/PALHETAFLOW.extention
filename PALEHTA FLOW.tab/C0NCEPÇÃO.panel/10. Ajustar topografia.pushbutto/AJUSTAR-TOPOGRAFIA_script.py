# -*- coding: utf-8 -*-
import clr
clr.AddReference('RevitServices')
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager

clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, Transaction, Toposolid, Floor, XYZ, Options, Solid, Face, ElementId

clr.AddReference("System")
from System.Collections.Generic import List

clr.AddReference("RevitNodes")
import Revit
clr.ImportExtensions(Revit.GeometryConversion)

# Obtendo a instância correta do Revit
uiapp = __revit__  # Garantindo acesso ao PyRevit
if not uiapp:
    raise Exception("Erro: O script deve ser executado dentro do Revit.")

uidoc = uiapp.ActiveUIDocument
doc = uidoc.Document

# Verifica se há um documento aberto
if not doc:
    raise Exception("Nenhum documento aberto. Abra um projeto antes de executar o script.")

# Função para obter seleção do usuário
def selecionar_elemento(mensagem):
    try:
        from Autodesk.Revit.UI.Selection import ObjectType
        ref = uidoc.Selection.PickObject(ObjectType.Element, mensagem)
        return doc.GetElement(ref.ElementId)
    except:
        return None

# Selecionar o piso de referência
piso = selecionar_elemento("Selecione o piso de referência")
if not piso or not isinstance(piso, Floor):
    raise Exception("Piso inválido ou não selecionado.")

# Selecionar a superfície topográfica (Toposolid no Revit 2025)
topografia = selecionar_elemento("Selecione a superfície topográfica")
if not topografia or not isinstance(topografia, Toposolid):
    raise Exception("Superfície topográfica inválida ou não selecionada.")

# Criando um objeto Options() para obter a geometria do piso
opt = Options()
opt.ComputeReferences = True
opt.IncludeNonVisibleObjects = False

# Obtendo a geometria do piso
altura_piso_inferior = None
piso_geo = piso.get_Geometry(opt)

# Buscando a face inferior do piso
for obj in piso_geo:
    if isinstance(obj, Solid) and obj.Volume > 0:
        for face in obj.Faces:
            if face.FaceNormal.Z < -0.99:  # Face inferior
                altura_piso_inferior = face.Origin.Z
                break
    if altura_piso_inferior:
        break

if not altura_piso_inferior:
    raise Exception("Não foi possível determinar a altura da face inferior do piso.")

# Obtendo os pontos da superfície do Toposolid
topo_geo = topografia.get_Geometry(opt)
pontos_originais = List[XYZ]()  # Criando lista do tipo correto

for obj in topo_geo:
    if isinstance(obj, Solid):
        for face in obj.Faces:
            if face.FaceNormal.Z > 0.99:  # Pegando a face superior
                mesh = face.Triangulate()  # Obtendo a malha da superfície
                for vertice in mesh.Vertices:
                    pontos_originais.Add(XYZ(vertice.X, vertice.Y, vertice.Z))

if pontos_originais.Count == 0:
    raise Exception("Nenhum ponto encontrado na topografia.")

pontos_atualizados = List[XYZ]()  # Lista correta para `Toposolid.Create()`

# Ajustando os pontos da topografia para ficarem na altura da face inferior do piso
for ponto in pontos_originais:
    novo_ponto = XYZ(ponto.X, ponto.Y, altura_piso_inferior)  # Nivelamento do terreno
    pontos_atualizados.Add(novo_ponto)

# Obtendo corretamente os elementos para recriação
toposolid_type_id = topografia.GetTypeId()  # Corrigido
level_id = topografia.LevelId  # Corrigido

if not level_id or not toposolid_type_id:
    raise Exception("Erro ao obter LevelId ou Toposolid TypeId.")

# Criando uma nova transação para editar o Toposolid
t = Transaction(doc, "Ajustar Topografia à Face Inferior do Piso")
t.Start()

try:
    # Criando um novo Toposolid com os parâmetros corretos
    novo_toposolid = Toposolid.Create(doc, level_id, toposolid_type_id, pontos_atualizados)

    # Excluindo o antigo Toposolid
    doc.Delete(topografia.Id)

    t.Commit()
    print("Topografia ajustada com sucesso à face inferior do piso!")
except Exception as e:
    t.RollBack()
    print("Erro ao modificar a topografia:", str(e))
