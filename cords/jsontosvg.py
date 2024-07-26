import json
import svgwrite

with open("imitators.json", 'r') as file:
    imitators = json.load(file))


with open("stands.json", 'r') as file:
    stands = json.load(file)


class Node:
    
    def __init__(self, node_data) -> None:
        self.x = node_data['position']['x']
        self.y = node_data['position']['y']
        self.id = node_data['data']['id']
        self.is_imitator = False
        self.is_stand = False
        
        if "imitator" in node_data['data'] and "angle" in node_data['data']:
            self.is_imitator = True
        if "stand" in node_data['data'] and 'angle' in node_data['data']:
            self.is_stand = True
            
        if not self.is_stand and not self.is_imitator:
            raise KeyError("Node is not a stand or imitator")


class Imitator:

    def __init__(self, node: Node, data_node, im) -> None:
        self.x = node.x
        self.y = node.y
        self.height_hole = im['dist_y']
        self.height_real = im['height_real']
        self.height_imag = im['height_imag']
        self.width_hole = im['dist_x']
        self.width_real = im['width_real']
        self.width_imag = im['width_imag']
        self.rot_angle = data_node['data']['angle']
        
        # if wrong angle
        if self.rot_angle not in {0, 90, 180, 270}:
            raise KeyError("Wrong angle of rotation in json file")

        # Division by two
        self.half_height_hole = self.height_hole >> 1
        self.half_height_real = self.height_real >> 1
        self.half_height_imag = self.height_imag >> 1
        self.half_width_hole = self.width_hole >> 1
        self.half_width_real = self.width_real >> 1
        self.half_width_imag = self.width_imag >> 1    
        
        # Displace center position to fit to grid
        if self.width_real != self.width_imag:
            if self.rot_angle in {0, 180}:
                self.x += 5
            elif self.rot_angle in {90, 270}:
                self.y += 5
        
        if self.height_imag != self.height_real:
            if self.rot_angle in {0, 180}:
                self.y += 5
            elif self.rot_angle in {90, 270}:
                self.x += 5
                
        # Array of imitator contour coordinates 
        self.coord_contour = [
            (self.x - self.half_width_real, self.y - self.half_height_real),
            (self.x + self.half_width_real, self.y - self.half_height_real), 
            (self.x + self.half_width_real, self.y + self.half_height_real),
            (self.x - self.half_width_real, self.y + self.half_height_real), 
            (self.x - self.half_width_real, self.y - self.half_height_real)
        ]
        
        # Array of mount holes coordinates
        self.coord_holes = [
            (self.x - self.half_width_hole, self.y - self.half_height_hole),
            (self.x + self.half_width_hole, self.y - self.half_height_hole),
            (self.x + self.half_width_hole, self.y + self.half_height_hole),
            (self.x - self.half_width_hole, self.y + self.half_height_hole),
        ] 
        
        # Сonnector label and imitator type label
        self.connector = data_node['data']['connector']
        self.type = data_node['data']['imitator']
        
        # Coordinates for connector label and imitator type label
        self.coord_connector = (self.x - self.half_width_real + 2, self.y - self.half_height_real - 2) 
        self.coord_type_imitator = (self.x - self.half_width_real + 18, self.y - self.half_height_real - 2)


class Stand:
    
    def __init__(self, node: Node, data_node, st) -> None:
        self.x = node.x
        self.y = node.y
        self.height = st['height']
        self.width = st['width']
        self.rot_angle = data_node['data']['angle']

        # Division by two
        self.half_height = self.height >> 1
        self.half_width = self.width >> 1   
        
        # Array of stand contour coordinates 
        self.coord_contour = [
            (self.x - self.half_width, self.y - self.half_height),
            (self.x + self.half_width, self.y - self.half_height), 
            (self.x + self.half_width, self.y + self.half_height),
            (self.x - self.half_width, self.y + self.half_height), 
            (self.x - self.half_width, self.y - self.half_height)
        ]
        
        # Array of mount holes coordinates
        self.coord_holes = []
        for hole in st['holes']:
            self.coord_holes.append((self.x + hole['x'], self.y + hole['y']))   
            
        # Stand label
        self.type = data_node['data']['stand']
        
        # Coordinates stand label
        self.coord_type_stand = (self.x - self.half_width + 2, self.y - self.half_height - 2)


class Edge:
    
    def __init__(self, data_edge) -> None:
        
        self.source_id = data_edge['data']['source']
        self.target_id = data_edge['data']['target']


class SVGCreator:
    
    def __init__(self) -> None:
        pass
    
        
    def create_svg_from_cytoscape_json(self, json_filename, svg_filename):
        with open(json_filename, 'r') as file:
            data = json.load(file)

        # Define the A0 size in mm
        drawing_width = 841
        drawing_height = 1189
        
        positions = {}

        dwg = svgwrite.Drawing(svg_filename, 
                            profile='full', 
                            size=(drawing_width, drawing_height))
        
        # Define layers
        draw_layer = dwg.g(id='draw')
        laser_layer = dwg.g(id='laser')
        grid_layer = dwg.g(id='grid')
        
        # Draw the red grid as a circles
        for i in range(0, drawing_width + 1, 10):
            for j in range(0, drawing_height + 1, 10):
                grid_layer.add(dwg.circle(center=(i, j), r=1, stroke='red', fill='none'))

        # Nodes
        for node_data in data['layout']['graph']['elements']['nodes']:
            cur_node = Node(node_data)
            cur_node.y = drawing_height - cur_node.y 
            positions[cur_node.id] = (cur_node.x, cur_node.y)
            
            # If node is imitator
            if cur_node.is_imitator:
                im = next((im for im in imitators if im['name'] == node_data['data']["imitator"]), None)

                if not im:
                    raise KeyError("Imitator not found")
                
                # Create Imitator
                cur_im = Imitator(cur_node, node_data, im)
                
                # Draw the rotated contour (rectangle) as a polyline (draw layer)
                contour = draw_layer.add(dwg.polygon(points=[pt for pt in cur_im.coord_contour], stroke='black', fill='none'))
                contour.rotate(cur_im.rot_angle, center=(cur_im.x, cur_im.y))
                
                # Draw the connector label and type imitator label
                connector_label = draw_layer.add(dwg.text(cur_im.connector, insert=(cur_im.coord_connector), fill='black', font_size=6, font_family='Montserrat'))
                connector_label.rotate(cur_im.rot_angle, center=(cur_im.x, cur_im.y))
                type_imitator_label = draw_layer.add(dwg.text(cur_im.type, insert=(cur_im.coord_type_imitator), fill='black', font_size=6, font_family='Montserrat'))
                type_imitator_label.rotate(cur_im.rot_angle, center=(cur_im.x, cur_im.y))
                        
                # Draw the rotated holes coordinates as a circles (laser layer)
                for hole in cur_im.coord_holes:                
                    cur_hole = laser_layer.add(dwg.circle(center=hole, r=1, stroke='black', fill='none'))
                    
                    # Rotate holes coordinates around the center
                    cur_hole.rotate(cur_im.rot_angle, center=(cur_im.x, cur_im.y))
            
            # If node is stand
            else:            
                st = next((st for st in stands if st['name'] == node_data['data']["stand"]), None)

                if not st:
                    raise KeyError("Stand not found")
                
                # Create Stand
                cur_st = Stand(cur_node, node_data, st)
                
                # Draw the rotated contour (rectangle) as a polyline (draw layer)
                contour = draw_layer.add(dwg.polygon(points=[pt for pt in cur_st.coord_contour], stroke='black', fill='none'))
                
                # Rotate contour coordintaes around the center 
                contour.rotate(cur_st.rot_angle, center=(cur_st.x, cur_st.y))
                
                # Draw the stand label        
                type_stand_label = draw_layer.add(dwg.text(cur_st.type, insert=(cur_st.coord_type_stand), fill='black', font_size=6, font_family='Montserrat'))
                type_stand_label.rotate(cur_st.rot_angle, center=(cur_st.x, cur_st.y))
                
                # Draw the rotated holes coordinates as a circles (laser layer)
                for hole in cur_st.coord_holes:                
                    cur_hole = laser_layer.add(dwg.circle(center=hole, r=1, stroke='black', fill='none'))
                    
                    # Rotate holes coordinates around the center
                    cur_hole.rotate(cur_st.rot_angle, center=(cur_st.x, cur_st.y))
                
        # Edges
        for edge_data in data['layout']['graph']['elements']['edges']:
            cur_ed = Edge(edge_data)
            
            source = positions[cur_ed.source_id]
            target = positions[cur_ed.target_id]

            # Draw the edge as a line
            draw_layer.add(dwg.line(start=source, end=target, stroke='black'))
        
        dwg.add(grid_layer)
        dwg.add(draw_layer)
        dwg.add(laser_layer)
            
        # Save the SVG file
        dwg.save()
        print(f"SVG file '{svg_filename}' created successfully.")      
