# -*- coding: utf-8 -*-
# Script para o PyRevit: Criação de conduite entre caixinha octogonal e tomada
# Compatível com IronPython 2

import clr
clr.AddReference("RevitAPI")
clr.AddReference("RevitServices")

from Autodesk.Revit.DB import *
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager

# Obter documento do Revit
try:
    uiapp = getattr(DocumentManager.Instance, 'CurrentUIApplication', None)
    doc = getattr(DocumentManager.Instance, 'CurrentDBDocument', None)

    if uiapp is None or doc is None:
        raise EnvironmentError("Erro: PyRevit não está carregado corretamente ou o ambiente não foi inicializado. Certifique-se de que o script está sendo executado pelo PyRevit com um projeto aberto.")

    uidoc = getattr(uiapp, 'ActiveUIDocument', None)
    if uidoc is None:
        raise EnvironmentError("Erro: Nenhum documento ativo detectado. Abra um projeto no Revit e tente novamente.")

    view = doc.ActiveView

    # Função para obter a localização de um elemento
    def get_element_location(element):
        location = element.Location
        if isinstance(location, LocationPoint):
            return location.Point
        elif isinstance(location, LocationCurve):
            return location.Curve.GetEndPoint(0)
        return None

    # Função principal
    def criar_conduite_entre_elementos():
        try:
            # Obter seleção
            selection_ids = uidoc.Selection.GetElementIds()
            if not selection_ids:
                print("Nenhum elemento selecionado. Selecione a caixinha octogonal e a tomada.")
                return

            selection = [doc.GetElement(elId) for elId in selection_ids]

            if len(selection) != 2:
                print("Selecione exatamente dois elementos: a caixinha octogonal e a tomada.")
                return

            # Identificar elementos (caixinha e tomada)
            caixa, tomada = selection

            # Obter localizações
            ponto_caixa = get_element_location(caixa)
            ponto_tomada = get_element_location(tomada)

            if not ponto_caixa or not ponto_tomada:
                print("Não foi possível obter as localizações dos elementos selecionados.")
                return

            # Iniciar transação
            TransactionManager.Instance.EnsureInTransaction(doc)

            # Criar o conduite (usando um duto ou condutor como exemplo)
            conduite_type = FilteredElementCollector(doc) \
                .OfClass(Electrical.ConduitType) \
                .FirstElement()

            if not conduite_type:
                print("Tipo de conduite elétrico não encontrado no projeto.")
                TransactionManager.Instance.ForceCloseTransaction()
                return

            # Criar o conduite entre os pontos
            conduit = Electrical.Conduit.Create(doc, conduite_type.Id, ponto_caixa, ponto_tomada, doc.ActiveView.GenLevel.Id)

            # Finalizar transação
            TransactionManager.Instance.TransactionTaskDone()
            print("Conduite criado com sucesso entre a caixinha octogonal e a tomada.")

        except Exception as e:
            TransactionManager.Instance.ForceCloseTransaction()
            print("Erro ao criar o conduite: {}".format(str(e)))

    # Executar a função principal
    if __name__ == "__main__":
        criar_conduite_entre_elementos()

except EnvironmentError as env_err:
    print(str(env_err))
except Exception as ex:
    print("Erro inesperado: {}".format(str(ex)))