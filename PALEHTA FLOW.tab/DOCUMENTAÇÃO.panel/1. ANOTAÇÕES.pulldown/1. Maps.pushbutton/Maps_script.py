# -*- coding: utf-8 -*-

import webbrowser
from pyrevit import forms
from pyrevit import revit

def obter_endereco_do_projeto():
    """
    Obt�m o endere�o do projeto a partir das propriedades do Revit.
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
    Permite ao usu�rio escolher entre usar o endere�o do projeto ou inserir um endere�o manualmente.
    """
    escolha = forms.alert("Escolha uma op��o", options=["Usar endere�o do projeto", "Digitar endere�o manualmente"])
    
    if escolha:
        if escolha == "Usar endere�o do projeto":
            endereco = obter_endereco_do_projeto()
            if not endereco:
                forms.alert("O projeto n�o possui um endere�o cadastrado. Insira manualmente.")
                endereco = forms.ask_for_string("Digite o endere�o ou coordenadas:")
        else:
            endereco = forms.ask_for_string("Digite o endere�o ou coordenadas:")
        
        if endereco:
            url = "https://www.google.com/maps/search/" + endereco.replace(" ", "+")
            webbrowser.open(url)

# Executar a fun��o para abrir o Google Maps
abrir_google_maps()
