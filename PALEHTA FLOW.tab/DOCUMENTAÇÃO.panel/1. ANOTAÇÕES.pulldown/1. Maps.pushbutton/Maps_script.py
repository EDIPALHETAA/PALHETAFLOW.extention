# -*- coding: utf-8 -*-

import webbrowser
from pyrevit import forms
from pyrevit import revit

def obter_endereco_do_projeto():
    """
    Obtém o endereço do projeto a partir das propriedades do Revit.
    """
    doc = revit.doc
    try:
        endereco_projeto = doc.ProjectInformation.Address
        if endereco_projeto:
            return endereco_projeto
    except:
        pass
    return None

def abrir_google_maps():
    """
    Permite ao usuário escolher entre usar o endereço do projeto ou inserir um endereço manualmente.
    """
    escolha = forms.alert("Escolha uma opção", options=["Usar endereço do projeto", "Digitar endereço manualmente"])
    
    if escolha:
        if escolha == "Usar endereço do projeto":
            endereco = obter_endereco_do_projeto()
            if not endereco:
                forms.alert("O projeto não possui um endereço cadastrado. Insira manualmente.")
                endereco = forms.ask_for_string("Digite o endereço ou coordenadas:")
        else:
            endereco = forms.ask_for_string("Digite o endereço ou coordenadas:")
        
        if endereco:
            url = "https://www.google.com/maps/search/" + endereco.replace(" ", "+")
            webbrowser.open(url)

# Executar a função para abrir o Google Maps
abrir_google_maps()
