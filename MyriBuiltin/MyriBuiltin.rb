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
        bed_rail_thickness: 1.5,
        walnut_front_thickness: 0.75
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
             inner_width, s[:walnut_front_thickness], 8, :walnut_solid, grain: :x),
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
      s = layout
      t = s[:panel_thickness]
      lt = left_thickness || t
      back = s[:back_thickness]
      recess = s[:back_recess]
      back_front = -recess - back
      brace_depth = s[:mounting_brace_thickness]
      brace_height = s[:mounting_brace_height]
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
      frame_depth = s[:face_frame_thickness]
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

    # Drawer fronts share the opening's inset reveals; boxes allow 1/2 inch
    # on each side for slides. All dimensions are finished inches.
    def drawer_parts(name, x, y, z, opening_width, front_height, front_name: "#{name} front")
      reveal = 0.125
      front_thickness = layout[:walnut_front_thickness]
      box_x = x + 0.5
      box_y = y + front_thickness
      box_z = z + 0.5
      box_width = opening_width - 1.0
      box_depth = 12.0
      box_height = front_height - 1.0
      wall = 0.5
      bottom = 0.25
      items = [
        part(front_name, x + reveal, y, z,
             opening_width - 2 * reveal, front_thickness, front_height, :walnut_solid),
        part("#{name} bottom", box_x, box_y, box_z,
             box_width, box_depth, bottom, :walnut_plywood)
      ]
      [box_x, box_x + box_width - wall].each_with_index do |side_x, index|
        items << part("#{name} side #{index + 1}", side_x, box_y, box_z + bottom,
                      wall, box_depth, box_height - bottom, :walnut_plywood)
      end
      [box_y, box_y + box_depth - wall].each_with_index do |end_y, index|
        items << part("#{name} end #{index + 1}", box_x + wall, end_y, box_z + bottom,
                      box_width - 2 * wall, wall, box_height - bottom, :walnut_plywood)
      end
      items
    end

    def nightstand_drawer_parts
      s = layout
      thickness = s[:panel_thickness]
      inner_x = s[:wall_width] - s[:tower_width] + thickness
      inner_width = s[:tower_width] - 2 * thickness
      reveal = 0.125
      front_height = (28 - thickness - 4 * reveal) / 3.0
      3.times.flat_map do |index|
        z = thickness + reveal + index * (front_height + reveal)
        drawer_parts("Nightstand drawer #{index + 1}", inner_x, -13.75, z, inner_width, front_height,
                     front_name: "Nightstand drawer front #{index + 1}")
      end
    end

    def desk_pedestal
      s = layout
      t = s[:panel_thickness]
      # The pedestal is a separate hollow box, rather than a solid placeholder.
      pedestal = carcass('D2 Desk drawer pedestal', 1, 0, 15, 29.25, depth: 22)
      reveal = 0.125
      drawer_height = (29.25 - 2 * t - 5 * reveal) / 4.0
      drawer_layout = [[0, 2 * drawer_height + reveal], [2, drawer_height], [3, drawer_height]]
      drawer_layout.each_with_index do |(slot, front_height), index|
        drawer_name = index.zero? ? 'Desk file drawer' : "Desk drawer #{index + 1}"
        front_z = t + reveal + slot * (drawer_height + reveal)
        pedestal[:parts].concat(drawer_parts(drawer_name, 1 + t, -22.75, front_z,
                                            15 - 2 * t, front_height))
      end
      # The pedestal fits in front of the surround's separate back panel.
      pedestal[:parts].each { |item| item[:origin][1] -= s[:back_recess] + s[:back_thickness] }
      pedestal
    end

    def assemblies
      s = layout
      desk_width = s[:filler_width] + s[:desk_width]
      tower_x = s[:wall_width] - s[:tower_width]
      t = s[:panel_thickness]
      reveal = 0.125
      # Half-inch installation clearance above boxes; loose scribe closes it.
      top = s[:cabinet_height] - 0.5
      modules = []
      desk = carcass('D1 Desk lower surround', 0, 0, desk_width, 48.75,
                     left_thickness: s[:filler_width], bottom: false)
      modules << desk
      modules << desk_pedestal
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
                               width - 2 * t - 2 * reveal, s[:walnut_front_thickness], top - 72 - 2 * t - 2 * reveal,
                               :walnut_solid, grain: :z)
        modules << cabinet
      end
      loose = [
        part('Desk top - install in room', 1, -24, 29.25, desk_width - 1 - t, 24 - s[:back_recess] - s[:back_thickness], 1.5, :walnut_solid),
        part('Desk LED', 2.5, -12.9, 47.65, 42, 0.4, 0.25, :led),
        part('Nightstand LED', tower_x + 1.5, -12.9, 47, s[:tower_width] - 3, 0.4, 0.25, :led)
      ]
      # [[0, desk_width], [desk_width, s[:bed_width]], [tower_x, s[:tower_width]]].each_with_index do |(x, width), index|
      #   loose << part("Ceiling scribe #{index + 1} - fit on site", x, -13.75, top,
      #                 width, 0.75, 0.5, :purpleheart_solid)
      # end
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
      consolidate_face_frames(modules)
      continuous_desk_face_frame(modules)
      continuous_horizontal_face_frame(modules, 'Desk top', s[:filler_width], desk_width - t,
                                       top - t, height: t, stile_edge: :top)
      bed_left = s[:filler_width] + s[:desk_width] + t
      continuous_horizontal_face_frame(modules, 'Bed', bed_left, bed_left + s[:bed_width] - 2 * t, 71.25)
      continuous_horizontal_face_frame(modules, 'Bed top', bed_left, bed_left + s[:bed_width] - 2 * t,
                                       top - t, height: t, stile_edge: :top)
      continuous_outer_face_frames(modules)
    end

    def continuous_outer_face_frames(modules)
      s = layout
      modules.each do |assembly|
        assembly[:parts].reject! do |item|
          next false unless item[:material] == :purpleheart_solid && item[:grain] == :z

          item[:origin][0].abs < 0.00001 ||
            (item[:origin][0] + item[:size][0] - s[:wall_width]).abs < 0.00001
        end
      end
      front = -s[:upper_depth] - s[:face_frame_thickness]
      height = s[:cabinet_height] - 0.5
      shared = modules.find { |assembly| assembly[:name].start_with?('I3 ') }
      shared[:parts] << part('Far left continuous purpleheart stile', 0, front, 0,
                             s[:filler_width], s[:face_frame_thickness], height, :purpleheart_solid, grain: :z)
      shared[:parts] << part('Far right continuous purpleheart stile', s[:wall_width] - s[:panel_thickness], front, 0,
                             s[:panel_thickness], s[:face_frame_thickness], height, :purpleheart_solid, grain: :z)
      modules
    end

    def continuous_desk_face_frame(modules)
      left = layout[:filler_width]
      right = left + layout[:desk_width] - layout[:panel_thickness]
      continuous_horizontal_face_frame(modules, 'Desk', left, right, 48.0)
    end

    def continuous_horizontal_face_frame(modules, label, left, right, bottom, height: 1.5, stile_edge: :bottom)
      top = bottom + height
      modules.each do |assembly|
        assembly[:parts].reject! do |item|
          item[:material] == :purpleheart_solid && item[:grain] == :x &&
            (item[:origin][2] - bottom).abs < 0.00001 &&
            item[:origin][0] >= left && item[:origin][0] + item[:size][0] <= right + 0.00001
        end
        assembly[:parts].each do |item|
          next unless item[:material] == :purpleheart_solid && item[:grain] == :z
          next unless item[:origin][0] >= left && item[:origin][0] + item[:size][0] <= right
          if stile_edge == :top
            if item[:origin][2] < bottom && item[:origin][2] + item[:size][2] > bottom
              item[:size][2] = bottom - item[:origin][2]
            end
            next
          end
          next unless item[:origin][2] < top && item[:origin][2] + item[:size][2] > top

          item[:size][2] -= top - item[:origin][2]
          item[:origin][2] = top
          item[:name] = label == 'Desk' ? 'Desk upper center purpleheart stile' : "Bed bridge purpleheart stile x#{item[:origin][0]}"
        end
      end
      shared = modules.find { |assembly| assembly[:name].start_with?('I4 ') }
      shared[:parts] << part("#{label} continuous horizontal purpleheart face frame", left,
                             -layout[:upper_depth] - layout[:face_frame_thickness], bottom,
                             right - left, layout[:face_frame_thickness], height, :purpleheart_solid, grain: :x)
      modules
    end

    # Shared stiles install after the boxes are joined. Split at module-height
    # changes so only the portions actually adjoining another box are combined.
    def consolidate_face_frames(modules, horizontal: false)
      if horizontal
        # Reuse the same seam union with X/Z exchanged for horizontal rails.
        modules.each do |assembly|
          assembly[:parts].each do |item|
            item[:origin][0], item[:origin][2] = item[:origin][2], item[:origin][0]
            item[:size][0], item[:size][2] = item[:size][2], item[:size][0]
          end
        end
      end
      candidates = []
      modules.each do |assembly|
        assembly[:parts].each do |item|
          next unless item[:material] == :purpleheart_solid && item[:name].include?('frame')
          next unless item[:size][2] > item[:size][0]

          candidates << [assembly, item]
        end
      end
      shared = []
      candidates.group_by { |_, item| [item[:origin][1], item[:size][1]] }.each_value do |entries|
        # Treat integer/float equivalents and roundoff at shared edges as one
        # boundary; otherwise the sweep can create zero-width frame fragments.
        levels = entries.flat_map { |_, p| [p[:origin][2], p[:origin][2] + p[:size][2]] }
                        .map { |value| value.to_f.round(6) }.uniq.sort
        entries.each { |assembly, item| assembly[:parts].delete(item) }
        levels.each_cons(2) do |low, high|
          active = entries.select do |_, p|
            p[:origin][2].to_f.round(6) <= low && (p[:origin][2] + p[:size][2]).to_f.round(6) >= high
          end
          active.sort_by! { |_, p| p[:origin][0] }
          runs = []
          active.each do |entry|
            previous = runs.last && runs.last.last[1]
            if previous && (previous[:origin][0] + previous[:size][0] - entry[1][:origin][0]).abs < 0.00001
              runs.last << entry
            else
              runs << [entry]
            end
          end
          runs.each do |run|
            owner, first = run.first
            width = run.sum { |_, p| p[:size][0] }
            name = if run.size > 1
                     "Shared purpleheart stile x#{first[:origin][0]} z#{low}-#{high}"
                   else
                     "#{first[:name]} z#{low}-#{high}"
                   end
            strip = part(name, first[:origin][0], first[:origin][1], low,
                         width, first[:size][1], high - low, :purpleheart_solid, grain: :z)
            if run.size > 1
              shared << strip
            else
              owner[:parts] << strip
            end
          end
        end
      end
      unless shared.empty?
        name = horizontal ? 'I4 Shared horizontal face frames - fit after installation' : 'I3 Shared face frames - fit after installation'
        modules << { name: name, shop_built: false, parts: shared }
      end
      modules.each do |assembly|
        strips = assembly[:parts].select { |p| p[:name].include?(' z') && p[:material] == :purpleheart_solid }
        strips.group_by { |p| [p[:origin][0], p[:origin][1], p[:size][0], p[:size][1]].map { |n| n.round(6) } }.each_value do |column|
          previous = nil
          column.sort_by { |p| p[:origin][2] }.each do |strip|
            if previous && (previous[:origin][2] + previous[:size][2] - strip[:origin][2]).abs < 0.00001
              previous[:size][2] += strip[:size][2]
              previous[:name] = previous[:name].sub(/ z.*$/, " z#{previous[:origin][2]}-#{previous[:origin][2] + previous[:size][2]}")
              assembly[:parts].delete(strip)
            else
              previous = strip
            end
          end
        end
      end
      if horizontal
        modules.each do |assembly|
          assembly[:parts].each do |item|
            item[:origin][0], item[:origin][2] = item[:origin][2], item[:origin][0]
            item[:size][0], item[:size][2] = item[:size][2], item[:size][0]
            next unless item[:material] == :purpleheart_solid && item[:name].include?(' z')

            item[:grain] = item[:size][0] > item[:size][2] ? :x : :z
            if assembly[:name].start_with?('I4')
              item[:name] = "Shared purpleheart rail x#{item[:origin][0]} z#{item[:origin][2]}"
            end
          end
        end
        modules
      else
        consolidate_face_frames(modules, horizontal: true)
      end
    end

    def parts
      assemblies.flat_map { |assembly| assembly[:parts] }
    end

    def build
      plan = assemblies
      planned_parts = plan.flat_map { |assembly| assembly[:parts] }
      validate_parts!(planned_parts)
      model = Sketchup.active_model
      model.start_operation('Rebuild Myri Built-in', true)
      operation_open = true

      previous_model_existed = remove_previous_model(model)
      materials = create_materials(model)
      root = model.entities.add_group
      root.name = 'Myri Built-in'
      root.set_attribute('MyriBuiltin', 'generated_root', true)

      plan.each do |assembly|
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
      add_myri_figure(root.entities, planned_parts.find { |item| item[:name] == 'Full mattress' })

      model.commit_operation
      operation_open = false
      model.active_view.zoom_extents unless previous_model_existed
      message = "Myri Built-in rebuilt: #{planned_parts.length} components"
      Sketchup.status_text = message
      puts(message)
      root
    rescue StandardError => error
      model.abort_operation if model && operation_open
      warn("Myri Built-in error: #{error.message}")
      warn(error.backtrace.join("\n"))
      raise
    end

    def validate_parts!(items)
      names = {}
      items.each do |item|
        name = item[:name]
        raise ArgumentError, "Duplicate part name: #{name}" if names[name]

        names[name] = true
        valid_size = item[:size].all? { |n| n.finite? && n >= 0.001 }
        valid_origin = item[:origin].all?(&:finite?)
        unless valid_size && valid_origin
          raise ArgumentError, "Invalid geometry for #{name}: #{item.inspect}"
        end
        next unless item[:taper_inset]

        unless item[:taper_inset].each_with_index.all? { |inset, axis| inset >= 0 && 2 * inset < item[:size][axis] }
          raise ArgumentError, "Invalid taper for #{name}"
        end
      end
    end

    private

    def add_myri_figure(entities, mattress)
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
      textures = wood_textures
      material_palette.each_with_object({}) do |(key, rgb), collection|
        name = "Myri #{key.to_s.split('_').map(&:capitalize).join(' ')}"
        material = model.materials[name] || model.materials.add(name)
        material.texture = nil
        material.color = Sketchup::Color.new(*rgb)
        settings = textures[key]
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

    def position_wood_texture(face, material, part_data, settings, axes)
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
      texture_settings = wood_textures.fetch(part_data[:material]) if material.texture
      axes = { x: Geom::Vector3d.new(1, 0, 0), y: Geom::Vector3d.new(0, 1, 0), z: Geom::Vector3d.new(0, 0, 1) } if material.texture
      definition.entities.grep(Sketchup::Face).each do |part_face|
        part_face.material = material
        position_wood_texture(part_face, material, part_data, texture_settings, axes) if material.texture
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
