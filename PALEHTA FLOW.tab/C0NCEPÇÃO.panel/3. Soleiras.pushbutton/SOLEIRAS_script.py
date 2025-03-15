# -*- coding: utf-8 -*-
from pyrevit import revit, DB, forms

def get_wall_width(wall):
    """ Obtém a largura real da parede de forma confiável, independentemente da orientação."""
    if isinstance(wall, DB.Wall):
        wall_type = wall.Document.GetElement(wall.GetTypeId())
        if wall_type:
            width_param = wall_type.LookupParameter("Width")
            if width_param and width_param.HasValue:
                return width_param.AsDouble()
        
        # Alternativa: Usar BoundingBox para determinar a largura correta
        bbox = wall.get_BoundingBox(None)
        if bbox:
            x_size = abs(bbox.Max.X - bbox.Min.X)
            y_size = abs(bbox.Max.Y - bbox.Min.Y)
            return min(x_size, y_size)
    
    return 0.2

def create_floor_at_doors():
    doc = revit.doc
    
    # Pergunta ao usuário se deseja criar pisos para todas as portas ou apenas uma
    choice = forms.alert(
        "Deseja criar piso para todas as portas ou selecionar uma única porta?",
        options=["Todas as portas", "Selecionar uma porta", "Cancelar"]
    )
    
    if choice == "Cancelar" or not choice:
        return
    
    if choice == "Selecionar uma porta":
        door = revit.pick_element("Selecione uma porta")
        if not door or not isinstance(door, DB.FamilyInstance) or door.Category.Id.IntegerValue != int(DB.BuiltInCategory.OST_Doors):
            forms.alert("Elemento selecionado não é uma porta.")
            return
        doors = [door]
    else:
        doors = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Doors).WhereElementIsNotElementType().ToElements()
    
    if not doors:
        return
    
    floor_types = DB.FilteredElementCollector(doc).OfClass(DB.FloorType).ToElements()
    if not floor_types:
        return
    
    floor_type_dict = {ft.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString(): ft for ft in floor_types}
    default_floor = "PROCELANATO ELIZABETH CARRARA CINZA AC 74X74CM"
    floor_type_name = forms.ask_for_one_item(
        sorted(floor_type_dict.keys()),
        default=default_floor if default_floor in floor_type_dict else list(floor_type_dict.keys())[0],
        title="Selecione o tipo de piso"
    )
    
    if not floor_type_name:
        return
    
    floor_type = floor_type_dict[floor_type_name]
    level_dict = {}
    
    with DB.Transaction(doc, "Criar pisos na base das portas") as t:
        t.Start()
        
        for door in doors:
            try:
                location = door.Location
                if not isinstance(location, DB.LocationPoint):
                    continue
                
                door_point = location.Point
                door_level = doc.GetElement(door.LevelId)
                
                if door_level.Id not in level_dict:
                    level_dict[door_level.Id] = door_level
                
                door_host = door.Host
                wall_width = get_wall_width(door_host)
                
                door_width_param = door.Symbol.get_Parameter(DB.BuiltInParameter.DOOR_WIDTH)
                door_width = door_width_param.AsDouble() if door_width_param and door_width_param.HasValue else 1.0
                
                wall_orientation = door_host.Orientation.Normalize()
                door_orientation = door.FacingOrientation.Normalize()
                
                if abs(door_orientation.X) > abs(door_orientation.Y):
                    vec_width = door_orientation.Normalize().Multiply(wall_width / 2)
                    vec_depth = door_orientation.CrossProduct(DB.XYZ.BasisZ).Normalize().Multiply(door_width / 2)
                else:
                    vec_width = door_orientation.CrossProduct(DB.XYZ.BasisZ).Normalize().Multiply(door_width / 2)
                    vec_depth = door_orientation.Normalize().Multiply(wall_width / 2)

                p1 = door_point - vec_width - vec_depth
                p2 = door_point + vec_width - vec_depth
                p3 = door_point + vec_width + vec_depth
                p4 = door_point - vec_width + vec_depth
                
                profile = DB.CurveLoop.Create([
                    DB.Line.CreateBound(p1, p2),
                    DB.Line.CreateBound(p2, p3),
                    DB.Line.CreateBound(p3, p4),
                    DB.Line.CreateBound(p4, p1)
                ])
                
                new_floor = DB.Floor.Create(doc, [profile], floor_type.Id, door_level.Id)
            except:
                continue
        
        t.Commit()

create_floor_at_doors()
