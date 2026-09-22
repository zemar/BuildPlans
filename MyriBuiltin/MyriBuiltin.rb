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
        desk_width: 44.625,
        bed_width: 58.75,
        tower_width: 23.625,
        upper_depth: 13.0,
        work_depth: 24.0,
        panel_thickness: 0.75,
        back_thickness: 0.25,
        back_recess: 0.75,
        mounting_brace_thickness: 0.75,
        mounting_brace_height: 3.0,
        face_frame_thickness: 0.75,
        person_standing_height: 56.0,
        person_kneeling_ratio: 5.0 / 7.0,
        bed_slat_count: 14,
        bed_slat_width: 3.5,
        bed_slat_thickness: 1.0,
        bed_ledge_drop: 1.0,
        bed_rail_thickness: 1.5
      }
    end

    def material_palette
      {
        walnut_solid: [107, 70, 45],
        walnut_plywood: [107, 70, 45],
        ash: [210, 190, 151],
        purpleheart_solid: [105, 50, 90],
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
        walnut_plywood: { file: 'walnut_plywood.png', width: 24.0, grain: :v, tint: nil },
        purpleheart_solid: { file: 'purpleheart_solid.png', width: 12.0, grain: :u, tint: nil }
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

    def bed_parts
      s = layout
      rail_top = 16.0
      ledge_top = rail_top - s[:bed_ledge_drop]
      slat_top = ledge_top + s[:bed_slat_thickness]
      # Slats span between side rails; distribute across the clear frame length.
      rail_thickness = s[:bed_rail_thickness]
      clear_length = 74.5
      slat_gap = (clear_length - s[:bed_slat_count] * s[:bed_slat_width]) / (s[:bed_slat_count] - 1)
      parts = [
        part('Bed left rail', 48 - rail_thickness, -78.5, 8, rail_thickness, 76, 8, :walnut_solid),
        part('Bed right rail', 102, -78.5, 8, rail_thickness, 76, 8, :walnut_solid),
        part('Bed footboard', 48 - rail_thickness, -80, 8, 54 + 2 * rail_thickness, rail_thickness, 8, :walnut_solid),
        part('Bed front left leg', 48 - rail_thickness, -80, 0, 3, rail_thickness, 8, :walnut_solid, grain: :z).merge(taper_inset: [0.5, 0.25]),
        part('Bed front right leg', 99 + rail_thickness, -80, 0, 3, rail_thickness, 8, :walnut_solid, grain: :z).merge(taper_inset: [0.5, 0.25]),
        part('Bed head rail', 48, -4, 8, 54, rail_thickness, 8, :walnut_solid),
        part('Bed left slat ledge', 48, -78.5, ledge_top - 1, 1, clear_length, 1, :walnut_solid),
        part('Bed right slat ledge', 101, -78.5, ledge_top - 1, 1, clear_length, 1, :walnut_solid),
        part('Full mattress', 48, -78, slat_top, 54, 75, 10, :linen),
        part('Bed bridge LED', 47.5, -14.15, 71.65, 55, 0.4, 0.25, :led)
      ]

      s[:bed_slat_count].times do |index|
        y = -78.5 + index * (s[:bed_slat_width] + slat_gap)
        parts << part("Ash bed slat #{index + 1}", 48, y, ledge_top,
                      54, s[:bed_slat_width], s[:bed_slat_thickness], :ash, grain: :x)
      end

      parts
    end

    def headboard_carcasses
      s = layout
      t = s[:panel_thickness]
      name = 'H1 Open headboard carcass'
      x = s[:filler_width] + s[:desk_width]
      width = s[:bed_width]
      inner_x = x + t
      inner_width = width - 2 * t
      parts = [
        part("#{name} back", inner_x, -1.0, t, inner_width, 0.25, 72 - 2 * t, :walnut_plywood),
        part("#{name} top mounting brace", inner_x, -0.75, 72 - t - 3,
             inner_width, 0.75, 3, :walnut_plywood),
        part("#{name} top cap", x, -13, 71.25, width, 13, t, :walnut_plywood),
        part("#{name} bottom", inner_x, -13, 0, inner_width, 13, t, :walnut_plywood),
        part("#{name} purpleheart top frame", inner_x, -13.75, 71.25,
             inner_width, 0.75, t, :purpleheart_solid),
        part("#{name} purpleheart bottom frame", inner_x, -13.75, 0,
             inner_width, 0.75, t, :purpleheart_solid),
        part('Headboard walnut bed attachment cross brace', inner_x, -2.5, 8,
             inner_width, 1.25, 8, :walnut_solid, grain: :x),
      ]
      # The frame fits between continuous sides with 1/8-inch clearance.
      [x, x + width - t].each_with_index do |side_x, index|
        parts << part("#{name} side #{index + 1}", side_x, -13, 0,
                      t, 13, 71.25, :walnut_plywood)
        parts << part("#{name} side #{index + 1} purpleheart frame", side_x, -13.75, 0,
                      t, 0.75, 72, :purpleheart_solid)
      end
      [{ name: name, shop_built: true, parts: parts }]
    end

    # Each entry is an independently transportable assembly. Coordinates remain
    # in installed position; build translates each group to its own local origin.
    def carcass(name, x, z, width, height, shelves: [], left_thickness: nil, bottom: true, depth: 13.0)
      t = layout[:panel_thickness]
      lt = left_thickness || t
      back = layout[:back_thickness]
      recess = layout[:back_recess]
      back_front = -recess - back
      brace_depth = layout[:mounting_brace_thickness]
      brace_height = layout[:mounting_brace_height]
      front = -depth
      inner_x = x + lt
      inner_width = width - lt - t
      edges = [
        part("#{name} left side", x, front, z, lt, depth, height, :walnut_plywood),
        part("#{name} right side", x + width - t, front, z, t, depth, height, :walnut_plywood),
        part("#{name} top", inner_x, front, z + height - t, inner_width, depth, t, :walnut_plywood)
      ]
      edges << part("#{name} bottom", inner_x, front, z, inner_width, depth, t, :walnut_plywood) if bottom
      shelves.each_with_index do |level, index|
        edges << part("#{name} shelf #{index + 1}", inner_x, front, level,
                      inner_width, depth + back_front, t, :walnut_plywood)
      end
      frame_depth = layout[:face_frame_thickness]
      frames = edges.map do |edge|
        px, py, pz = edge[:origin]
        w, _, h = edge[:size]
        part("#{edge[:name]} purpleheart frame", px, py - frame_depth, pz,
             w, frame_depth, h, :purpleheart_solid, grain: h > w ? :z : :x)
      end
      { name: name, shop_built: true, parts: edges + frames + [
        part("#{name} back", inner_x, back_front, z + (bottom ? t : 0),
             inner_width, back, height - t - (bottom ? t : 0), :walnut_plywood),
        part("#{name} top mounting brace", inner_x, -brace_depth, z + height - t - brace_height,
             inner_width, brace_depth, brace_height, :walnut_plywood)
      ] }
    end

    def nightstand_drawer_parts
      s = layout
      thickness = s[:panel_thickness]
      inner_x = s[:wall_width] - s[:tower_width] + thickness
      inner_width = s[:tower_width] - 2 * thickness
      parts = []
      # Inset fronts with 1/8-inch reveals; boxes allow 1/2 inch per side
      # for slides. Hardware is not modeled.
      reveal = 0.125
      front_height = (28 - thickness - 4 * reveal) / 3.0
      box_x = inner_x + 0.5
      box_width = inner_width - 1.0
      box_depth = 12.0
      box_wall = 0.5
      box_bottom = 0.25
      3.times do |index|
        z = thickness + reveal + index * (front_height + reveal)
        parts << part("Nightstand drawer front #{index + 1}", inner_x + reveal, -13.75, z,
                      inner_width - 2 * reveal, 0.55, front_height, :walnut_solid)
        box_z = z + 0.5
        box_height = front_height - 1.0
        box_y = -13.2
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

      parts
    end

    def assemblies
      s = layout
      desk_width = s[:filler_width] + s[:desk_width]
      tower_x = s[:wall_width] - s[:tower_width]
      t = s[:panel_thickness]
      # Half-inch installation clearance above boxes; loose scribe closes it.
      top = s[:cabinet_height] - 0.5
      modules = []
      desk = carcass('D1 Desk lower surround', 0, 0, desk_width, 48.75,
                     left_thickness: s[:filler_width], bottom: false)
      modules << desk
      # The pedestal is a separate hollow box, rather than a solid placeholder.
      pedestal = carcass('D2 Desk drawer pedestal', 1, 0, 15, 29.25, depth: 22)
      reveal = 0.125
      drawer_height = (29.25 - 2 * t - 5 * reveal) / 4.0
      4.times do |index|
        front_z = t + reveal + index * (drawer_height + reveal)
        pedestal[:parts] << part("Desk drawer front #{index + 1}", 1 + t + reveal, -22.75,
                                  front_z,
                                  15 - 2 * t - 2 * reveal, 0.55, drawer_height, :walnut_solid)
        box_x = 1 + t + 0.5
        box_width = 15 - 2 * t - 1
        box_y = -22.2
        box_depth = 12.0
        box_z = front_z + 0.5
        box_height = drawer_height - 1
        pedestal[:parts] << part("Desk drawer #{index + 1} bottom", box_x, box_y, box_z,
                                 box_width, box_depth, 0.25, :walnut_plywood)
        [box_x, box_x + box_width - 0.5].each_with_index do |x, side|
          pedestal[:parts] << part("Desk drawer #{index + 1} side #{side + 1}", x, box_y, box_z + 0.25,
                                   0.5, box_depth, box_height - 0.25, :walnut_plywood)
        end
        [box_y, box_y + box_depth - 0.5].each_with_index do |y, end_index|
          pedestal[:parts] << part("Desk drawer #{index + 1} end #{end_index + 1}", box_x + 0.5, y, box_z + 0.25,
                                   box_width - 1, 0.5, box_height - 0.25, :walnut_plywood)
        end
      end
      # The pedestal fits in front of the surround's separate back panel.
      pedestal[:parts].each { |item| item[:origin][1] -= s[:back_recess] + s[:back_thickness] }
      modules << pedestal
      # Two separate boxes replace the shared central upright.
      modules << carcass('D3 Desk upper left', 0, 48.75, 23.5, top - 48.75,
                         left_thickness: s[:filler_width], shelves: [60, 72, 84])
      modules << carcass('D4 Desk upper right', 23.5, 48.75, desk_width - 23.5, top - 48.75,
                         shelves: [60, 72, 84])
      nightstand = carcass('N1 Nightstand drawers', tower_x, 0, s[:tower_width], 28.75)
      nightstand[:parts].concat(nightstand_drawer_parts)
      modules << nightstand
      modules << carcass('N2 Nightstand cubby', tower_x, 28.75, s[:tower_width], 19.25)
      modules << carcass('N3 Nightstand upper', tower_x, 48, s[:tower_width], top - 48,
                         shelves: [60, 72, 84])
      3.times do |index|
        width = s[:bed_width] / 3.0
        x = desk_width + index * width
        cabinet = carcass("B#{index + 1} Bridge cabinet", x, 72, width, top - 72)
        cabinet[:parts] << part("Bridge door #{index + 1}", x + t + reveal,
                               -s[:upper_depth] - s[:face_frame_thickness], 72 + t + reveal,
                               width - 2 * t - 2 * reveal, 0.6, top - 72 - 2 * t - 2 * reveal,
                               :walnut_plywood, grain: :z)
        modules << cabinet
      end
      loose = [
        part('Desk top - install in room', 1, -24, 29.25, desk_width - 1 - t, 24 - s[:back_recess] - s[:back_thickness], 1.5, :walnut_solid),
        part('Desk LED', 2.5, -12.9, 47.65, 42, 0.4, 0.25, :led),
        part('Nightstand LED', tower_x + 1.5, -12.9, 47, s[:tower_width] - 3, 0.4, 0.25, :led)
      ]
      [[0, desk_width], [desk_width, s[:bed_width]], [tower_x, s[:tower_width]]].each_with_index do |(x, width), index|
        loose << part("Ceiling scribe #{index + 1} - fit on site", x, -13.75, top,
                      width, 0.75, 0.5, :purpleheart_solid)
      end
      modules.concat(headboard_carcasses)
      modules << { name: 'I1 Site-installed top, trim and lighting', shop_built: false, parts: loose }
      bed_groups = bed_parts.group_by do |item|
        case item[:name]
        when /Bed left rail|Bed left slat ledge/ then 'F1 Bed left rail and ledge'
        when /Bed right rail|Bed right slat ledge/ then 'F2 Bed right rail and ledge'
        when /Bed footboard|Bed front/ then 'F3 Bed foot assembly'
        else 'I2 Bed parts - assemble in room'
        end
      end
      bed_groups.each do |name, items|
        modules << { name: name, shop_built: !name.start_with?('I'), parts: items }
      end
      modules
    end

    def parts
      assemblies.flat_map { |assembly| assembly[:parts] }
    end

    def build
      model = Sketchup.active_model
      model.start_operation('Rebuild Myri Built-in', true)

      previous_model_existed = remove_previous_model(model)
      materials = create_materials(model)
      root = model.entities.add_group
      root.name = 'Myri Built-in'
      root.set_attribute('MyriBuiltin', 'generated_root', true)

      assemblies.each do |assembly|
        group = root.entities.add_group
        group.name = assembly[:name]
        group.set_attribute('MyriBuiltin', 'shop_built', assembly[:shop_built])
        origin = 3.times.map { |axis| assembly[:parts].map { |item| item[:origin][axis] }.min }
        assembly[:parts].each do |item|
          local_origin = 3.times.map { |axis| item[:origin][axis] - origin[axis] }
          add_component(model, group.entities, materials, item.merge(origin: local_origin))
        end
        group.transform!(Geom::Transformation.translation(origin))
      end
      add_myri_figure(root.entities)

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

    def add_myri_figure(entities)
      path = File.join(__dir__, 'myri_hark_kneeling.png')
      unless File.file?(path)
        warn("Missing figure image: #{path}")
        return
      end

      # This is a flat photo cutout, not a posed 3D human model.
      # Approximate upright kneeling height for a 56-inch standing person.
      # Alpha bounds in the 1024x1536 image: [87, 32, 834, 1468].
      # Account for transparent padding rather than scaling the whole canvas
      # to the person's height or floating the knees above the mattress.
      s = layout
      kneeling_height = s[:person_standing_height] * s[:person_kneeling_ratio]
      inches_per_pixel = kneeling_height / (1468 - 32)
      mattress = bed_parts.find { |item| item[:name] == 'Full mattress' }
      x, y, z = mattress[:origin]
      width, depth, height = mattress[:size]
      origin = [x + width / 2.0 - (87 + 834) / 2.0 * inches_per_pixel,
                y + depth / 4.0,
                z + height - (1536 - 1468) * inches_per_pixel]

      figure = entities.add_group
      figure.name = 'Myri Hark - kneeling (4 ft 8 in standing)'
      picture = figure.entities.add_image(path, [0, 0, 0], 1024 * inches_per_pixel)
      raise 'Could not load Myri kneeling image' unless picture

      # Stand the image upright in the XZ plane, facing the front of the bed.
      rotation = Geom::Transformation.rotation([0, 0, 0], [1, 0, 0], Math::PI / 2)
      figure.transform!(Geom::Transformation.translation(origin) * rotation)
      figure.casts_shadows = false
      figure.set_attribute('MyriBuiltin', 'standing_height_in', s[:person_standing_height])
      figure.set_attribute('MyriBuiltin', 'kneeling_height_in', kneeling_height)
      figure
    end

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
            warn("Missing wood texture: #{path}; using fallback color")
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
