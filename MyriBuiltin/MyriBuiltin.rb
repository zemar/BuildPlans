# frozen_string_literal: true

# Myri Built-in
# A measured, rebuildable SketchUp model for a 128 x 96 inch bedroom wall.
#
# Development:
#   1. Open this folder in VS Code.
#   2. In SketchUp's Ruby Console, load MyriBuiltin_LiveReload.rb once.
#   3. Save this file. SketchUp will rebuild the model automatically.

module MyriBuiltin
  class << self
    # Main dimensions are in inches. These are the first values to edit.
    def layout
      {
        wall_width: 128.0,
        wall_height: 96.0,
        cabinet_height: 96.0,
        filler_width: 1.0,
        desk_width: 45.0,
        bed_width: 58.0,
        tower_width: 24.0,
        upper_depth: 12.0,
        work_depth: 24.0,
        panel_thickness: 0.75,
        back_thickness: 0.25,
        bed_slat_count: 14,
        bed_slat_width: 3.5,
        bed_slat_thickness: 1.0,
        bed_ledge_drop: 1.0
      }
    end

    def material_palette
      {
        walnut_solid: [107, 70, 45],
        walnut_plywood: [107, 70, 45],
        ash: [210, 190, 151],
        linen: [227, 214, 189],
        wall: [214, 207, 191],
        floor: [168, 125, 79],
        led: [255, 158, 46]
      }
    end

    # Widths are estimated image coverage in inches, not board/sheet sizes.
    # nil tint preserves the photograph's color; set an RGB array to tint it.
    def wood_textures
      {
        walnut_solid: { file: 'walnut_solid.png', width: 12.0, grain: :u, tint: nil },
        walnut_plywood: { file: 'walnut_plywood.png', width: 24.0, grain: :v, tint: nil }
      }
    end

    def part(name, x, y, z, width, depth, height, material, grain: nil)
      {
        name: name,
        origin: [x, y, z],
        size: [width, depth, height],
        material: material,
        grain: grain || [:x, :y, :z][[width, depth, height].each_with_index.max_by { |size, _| size }.last]
      }
    end

    def room_parts
      s = layout
      [
        # part('Wall', 0, 0, 0, s[:wall_width], 1, s[:wall_height], :wall),
        # part('Floor', -8, -100, -1, 144, 105, 1, :floor),
        part('Left filler', 0, -12, 0, 1, 12, s[:cabinet_height], :walnut_solid),
      ]
    end

    def back_and_divider_parts
      s = layout
      [
        part('Desk and shelving back panel', 1, -0.25, 0, 45, 0.25, s[:cabinet_height], :walnut_plywood),
        part('Bed and bridge back panel', 46, -0.25, 0, 58, 0.25, 72, :walnut_plywood),
        part('Nightstand tower back panel', 104, -0.25, 0, s[:tower_width], 0.25, s[:cabinet_height], :walnut_plywood),
        part('Desk bed divider panel', 45.24, -12, 0, 0.75, 12, 60, :walnut_plywood)
      ]
    end

    def desk_parts
      s = layout
      parts = [
        part('Desk drawer cabinet', 1, -22, 0, 15, 22, 29.25, :walnut_plywood),
        part('Desk top', 1, -24, 29.25, 45, 24, 1.5, :walnut_solid),
        part('Desk shelf left side', 1, -12, 48, 0.75, 12, s[:cabinet_height] - 48, :walnut_plywood),
        part('Desk shelf middle divider', 23.125, -12, 48, 0.75, 12, s[:cabinet_height] - 48, :walnut_plywood),
        part('Desk shelf right side', 45.25, -12, 48, 0.75, 12, s[:cabinet_height] - 48, :walnut_plywood),
        part('Desk LED', 2.5, -11.9, 47.65, 42, 0.4, 0.25, :led)
      ]

      4.times do |index|
        z = 0.18 + (index * 7.2675)
        parts << part("Desk drawer front #{index + 1}", 1.12, -22.55, z,
                      14.76, 0.55, 7.0875, :walnut_solid)
      end

      [48, 60, 72, 84, s[:cabinet_height] - s[:panel_thickness]].each_with_index do |z, index|
        parts << part("Desk shelf #{index + 1}", 1, -12, z,
                      45, 12, 0.75, :walnut_plywood)
      end
      parts
    end

    def bed_parts
      s = layout
      rail_top = 16.0
      ledge_top = rail_top - s[:bed_ledge_drop]
      slat_top = ledge_top + s[:bed_slat_thickness]
      # Slats span between side rails; distribute across the clear frame length.
      clear_length = 74.5
      slat_gap = (clear_length - s[:bed_slat_count] * s[:bed_slat_width]) / (s[:bed_slat_count] - 1)
      parts = [
        part('Headboard backing', 46, -1.5, 0, 58, 1.5, 50, :walnut_plywood),
        part('Headboard left panel', 47.5, -2.2, 20, 27.25, 0.7, 28, :walnut_plywood),
        part('Headboard right panel', 75.25, -2.2, 20, 27.25, 0.7, 28, :walnut_plywood),
        part('Bed left rail', 46, -78, 8, 2, 76.5, 8, :walnut_solid),
        part('Bed right rail', 102, -78, 8, 2, 76.5, 8, :walnut_solid),
        part('Bed footboard', 46, -80, 8, 58, 2, 8, :walnut_solid),
        part('Bed front left leg', 46, -80, 0, 3, 2, 8, :walnut_solid, grain: :z).merge(taper_inset: [0.5, 0.25]),
        part('Bed front right leg', 101, -80, 0, 3, 2, 8, :walnut_solid, grain: :z).merge(taper_inset: [0.5, 0.25]),
        part('Bed head rail', 48, -3.5, 8, 54, 2, 8, :walnut_solid),
        part('Bed left slat ledge', 48, -78, ledge_top - 1, 1, clear_length, 1, :walnut_solid),
        part('Bed right slat ledge', 101, -78, ledge_top - 1, 1, clear_length, 1, :walnut_solid),
        part('Full mattress', 48, -78, slat_top, 54, 75, 10, :linen),
        part('Bed bridge cabinet', 46, -12, 72, 58, 12, s[:cabinet_height] - 72, :walnut_plywood),
        part('Bed bridge LED', 47.5, -11.9, 71.65, 55, 0.4, 0.25, :led)
      ]

      s[:bed_slat_count].times do |index|
        y = -78 + index * (s[:bed_slat_width] + slat_gap)
        parts << part("Ash bed slat #{index + 1}", 48, y, ledge_top,
                      54, s[:bed_slat_width], s[:bed_slat_thickness], :ash, grain: :x)
      end

      3.times do |index|
        x = 46.25 + (index * 19.33333)
        parts << part("Bridge door #{index + 1}", x, -12.6, 72.25,
                      18.83333, 0.6, s[:cabinet_height] - 72.5, :walnut_plywood)
      end
      parts
    end

    def nightstand_parts
      s = layout
      thickness = s[:panel_thickness]
      left = 104.0
      width = s[:tower_width]
      inner_x = left + thickness
      inner_width = width - 2 * thickness
      depth = s[:upper_depth] - s[:back_thickness]
      parts = [
        part('Nightstand carcass left side', left, -12, 0,
             thickness, depth, s[:cabinet_height], :walnut_plywood),
        part('Nightstand carcass right side', left + width - thickness, -12, 0,
             thickness, depth, s[:cabinet_height], :walnut_plywood),
        part('Nightstand carcass bottom', inner_x, -12, 0,
             inner_width, depth, thickness, :walnut_plywood),
        part('Nightstand cubby bottom', inner_x, -12, 28,
             inner_width, depth, thickness, :walnut_plywood),
        part('Nightstand cubby top', inner_x, -12, 47.25,
             inner_width, depth, thickness, :walnut_plywood),
        part('Nightstand LED', 105.5, -11.9, 47, width - 3, 0.4, 0.25, :led)
      ]

      # Inset fronts with 1/8-inch reveals; boxes allow 1/2 inch per side
      # for slides. Hardware is not modeled.
      reveal = 0.125
      front_height = (28 - thickness - 4 * reveal) / 3.0
      box_x = inner_x + 0.5
      box_width = inner_width - 1.0
      box_depth = 10.5
      box_wall = 0.5
      box_bottom = 0.25
      3.times do |index|
        z = thickness + reveal + index * (front_height + reveal)
        parts << part("Nightstand drawer front #{index + 1}", inner_x + reveal, -12, z,
                      inner_width - 2 * reveal, 0.55, front_height, :walnut_solid)
        box_z = z + 0.5
        box_height = front_height - 1.0
        box_y = -11.45
        parts << part("Nightstand drawer #{index + 1} bottom", box_x, box_y, box_z,
                      box_width, box_depth, box_bottom, :walnut_plywood)
        [box_x, box_x + box_width - box_wall].each_with_index do |x, side|
          parts << part("Nightstand drawer #{index + 1} side #{side + 1}", x, box_y, box_z + box_bottom,
                        box_wall, box_depth, box_height - box_bottom, :walnut_plywood)
        end
        [box_y, box_y + box_depth - box_wall].each_with_index do |y, end_index|
          parts << part("Nightstand drawer #{index + 1} end #{end_index + 1}", box_x + box_wall, y, box_z + box_bottom,
                        box_width - 2 * box_wall, box_wall, box_height - box_bottom, :walnut_plywood)
        end
      end

      [60, 72, 84, s[:cabinet_height] - thickness].each_with_index do |z, index|
        parts << part("Tower shelf #{index + 1}", inner_x, -12, z,
                      inner_width, depth, thickness, :walnut_plywood)
      end
      parts
    end

    def parts
      room_parts + back_and_divider_parts + desk_parts + bed_parts + nightstand_parts
    end

    def build
      model = Sketchup.active_model
      model.start_operation('Rebuild Myri Built-in', true)

      previous_model_existed = remove_previous_model(model)
      materials = create_materials(model)
      root = model.entities.add_group
      root.name = 'Myri Built-in'
      root.set_attribute('MyriBuiltin', 'generated_root', true)

      parts.each do |part_data|
        add_component(model, root.entities, materials, part_data)
      end

      model.commit_operation
      model.active_view.zoom_extents unless previous_model_existed
      Sketchup.status_text = "Myri Built-in rebuilt: #{parts.length} components"
      puts("Myri Built-in rebuilt: #{parts.length} components")
      root
    rescue StandardError => error
      model.abort_operation if model
      warn("Myri Built-in error: #{error.message}")
      warn(error.backtrace.join("\n"))
      raise
    end

    private

    def remove_previous_model(model)
      previous_groups = model.entities.grep(Sketchup::Group).select do |group|
        generated = group.get_attribute('MyriBuiltin', 'generated_root', false)
        generated || group.name == 'Myri Built-in' || group.name == 'Walnut Bedroom Built-in'
      end
      previous_groups.each(&:erase!)
      !previous_groups.empty?
    end

    def create_materials(model)
      material_palette.each_with_object({}) do |(key, rgb), collection|
        name = "Myri #{key.to_s.split('_').map(&:capitalize).join(' ')}"
        material = model.materials[name] || model.materials.add(name)
        material.texture = nil
        material.color = Sketchup::Color.new(*rgb)
        settings = wood_textures[key]
        if settings
          path = File.join(__dir__, settings[:file])
          if File.file?(path)
            # A single width preserves the source image's aspect ratio.
            material.texture = [path, settings[:width].inch]
            material.color = Sketchup::Color.new(*settings[:tint]) if settings[:tint]
          else
            warn("Missing walnut texture: #{path}; using fallback color")
          end
        end
        collection[key] = material
      end
    end

    def position_wood_texture(face, material, part_data)
      axes = {
        x: Geom::Vector3d.new(1, 0, 0),
        y: Geom::Vector3d.new(0, 1, 0),
        z: Geom::Vector3d.new(0, 0, 1)
      }
      # On end faces, use the longest remaining in-plane dimension.
      candidates = axes.keys.select { |axis| face.normal.dot(axes[axis]).abs < 0.999 }
      grain_axis = part_data[:grain]
      unless candidates.include?(grain_axis)
        grain_axis = candidates.max_by { |axis| part_data[:size][axes.keys.index(axis)] }
      end
      # Project grain onto the face so tapered legs retain vertical grain.
      direction = axes.fetch(grain_axis)
      normal = face.normal
      dot = normal.dot(direction)
      along = Geom::Vector3d.new(
        direction.x - normal.x * dot,
        direction.y - normal.y * dot,
        direction.z - normal.z * dot
      ).normalize
      across = face.normal.cross(along)
      settings = wood_textures.fetch(part_data[:material])
      u_axis, v_axis = settings[:grain] == :u ? [along, across] : [across, along]
      origin = face.vertices.first.position
      mapping = [
        origin, Geom::Point3d.new(0, 0, 0),
        origin.offset(u_axis, material.texture.width), Geom::Point3d.new(1, 0, 0),
        origin.offset(v_axis, material.texture.height), Geom::Point3d.new(0, 1, 0)
      ]
      face.position_material(material, mapping, true)
    end

    def add_component(model, parent_entities, materials, part_data)
      name = part_data[:name]
      width, depth, height = part_data[:size]
      definition_name = "MyriBuiltin - #{name}"
      definition = model.definitions[definition_name] || model.definitions.add(definition_name)
      definition.entities.clear!

      if part_data[:taper_inset]
        add_tapered_leg(definition.entities, width, depth, height, part_data[:taper_inset])
      else
        add_box(definition.entities, width, depth, height)
      end
      material = materials.fetch(part_data[:material])
      definition.entities.grep(Sketchup::Face).each do |part_face|
        part_face.material = material
        position_wood_texture(part_face, material, part_data) if material.texture
      end

      x, y, z = part_data[:origin]
      transform = Geom::Transformation.translation([x.inch, y.inch, z.inch])
      instance = parent_entities.add_instance(definition, transform)
      instance.name = name
      instance.material = materials.fetch(part_data[:material])

      definition.set_attribute('MyriBuiltin', 'generated_part', true)
      definition.set_attribute('MyriBuiltin', 'width_in', width)
      definition.set_attribute('MyriBuiltin', 'depth_in', depth)
      definition.set_attribute('MyriBuiltin', 'height_in', height)
      instance
    end

    def add_box(entities, width, depth, height)
      points = [
        [0, 0, 0],
        [width.inch, 0, 0],
        [width.inch, depth.inch, 0],
        [0, depth.inch, 0]
      ]
      face = entities.add_face(points)
      face.reverse! if face.normal.z.negative?
      face.pushpull(height.inch)
    end

    def add_tapered_leg(entities, width, depth, height, inset)
      ix, iy = inset
      bottom = [[ix, iy, 0], [width - ix, iy, 0],
                [width - ix, depth - iy, 0], [ix, depth - iy, 0]]
      top = [[0, 0, height], [width, 0, height],
             [width, depth, height], [0, depth, height]]
      bottom = bottom.map { |point| point.map(&:inch) }
      top = top.map { |point| point.map(&:inch) }
      entities.add_face(bottom.reverse)
      entities.add_face(top)
      4.times do |index|
        following = (index + 1) % 4
        entities.add_face([bottom[index], bottom[following], top[following], top[index]])
      end
    end
  end
end

MyriBuiltin.build
