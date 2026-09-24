# frozen_string_literal: true

# Myri Built-in 2
# A measured, rebuildable SketchUp model for a 128 x 96 inch bedroom wall.
#
# Development:
#   1. Open this folder in VS Code.
#   2. In SketchUp's Ruby Console, load MyriBuiltin2_LiveReload.rb once.
#   3. Save this file. SketchUp will rebuild the model automatically.

module MyriBuiltin2
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
        bed_slat_thickness: 0.5,
        bed_ledge_drop: 1.0,
        led_back_clearance: 0.75,
        show_led_illumination: true,
        bed_rail_thickness: 1.5,
        walnut_front_thickness: 0.75
      }
    end

    def material_palette
      {
        walnut_solid: [107, 70, 45],
        walnut_plywood: [107, 70, 45],
        baltic_birch_plywood: [224, 207, 169],
        maple_solid: [181, 151, 114],
        purpleheart_solid: [105, 50, 90],
        linen: [227, 214, 189],
        wall: [214, 207, 191],
        floor: [168, 125, 79],
        led: [255, 158, 46]
      }
    end

    # OpenCutList types: Solid Wood = 1, Sheet Goods = 2, Hardware = 5.
    def material_types
      {
        maple_solid: 1,
        walnut_solid: 1,
        purpleheart_solid: 1,
        walnut_plywood: 2,
        baltic_birch_plywood: 2,
        led: 5,
        linen: 5
      }
    end

    # OpenCutList stock thicknesses, with explicit units independent of model units.
    def material_stock_thicknesses
      {
        walnut_solid: ['0.75"', '1.5"'],
        walnut_plywood: ['0.25"', '0.75"'],
        baltic_birch_plywood: ['0.5"'],
        maple_solid: ['0.5"'],
        purpleheart_solid: ['0.75"']
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
      middle_ledge_x = 48 + 54 / 2.0 - 1.5 / 2.0
      parts = [
        part('Bed left rail', 48 - rail_thickness, -78.5, 8, rail_thickness, 76, 8, :walnut_solid),
        part('Bed right rail', 102, -78.5, 8, rail_thickness, 76, 8, :walnut_solid),
        part('Bed footboard', 48 - rail_thickness, -80, 8, 54 + 2 * rail_thickness, rail_thickness, 8, :walnut_solid),
        part('Bed front left leg', 48 - rail_thickness, -80, 0, 3, rail_thickness, 8, :walnut_solid, grain: :z).merge(taper_inset: [0.5, 0.25]),
        part('Bed front right leg', 99 + rail_thickness, -80, 0, 3, rail_thickness, 8, :walnut_solid, grain: :z).merge(taper_inset: [0.5, 0.25]),
        part('Bed head rail', 48, -4, 8, 54, rail_thickness, 8, :walnut_solid),
        part('Bed left slat ledge', 48, -78.5, ledge_top - 0.75, 1, clear_length, 0.75, :walnut_solid),
        part('Bed right slat ledge', 101, -78.5, ledge_top - 0.75, 1, clear_length, 0.75, :walnut_solid),
        part('Bed center slat ledge', middle_ledge_x, -78.5, ledge_top - 1, 3.0, clear_length, 1.5, :walnut_solid),
        part('Full mattress', 48, -78, slat_top, 54, 75, 10, :linen),
        led_strip('Bed bridge LED', 47.5, 71.25, 55)
      ]

      s[:bed_slat_count].times do |index|
        y = -78.5 + index * (s[:bed_slat_width] + slat_gap)
        parts << part('Maple solid bed slat', 48, y, ledge_top,
                      54, s[:bed_slat_width], s[:bed_slat_thickness], :maple_solid, grain: :x)
                      .merge(definition_name: 'Maple solid bed slat')
      end

      parts
    end

    def led_strip(name, x, panel_underside, width)
      s = layout
      depth = 0.4
      height = 0.25
      back_front = -s[:back_recess] - s[:back_thickness]
      y = back_front - s[:led_back_clearance] - depth
      part(name, x, y, panel_underside - height, width, depth, height, :led)
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
      [fit_carcass_back({ name: name, shop_built: true, parts: parts })]
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
      fit_carcass_back({ name: name, shop_built: true, parts: edges + frames + [
        part("#{name} back", inner_x, back_front, z + (bottom ? t : 0),
             inner_width, back, height - t - (bottom ? t : 0), :walnut_plywood),
        part("#{name} top mounting brace", inner_x, -brace_depth, z + height - t - brace_height,
             inner_width, brace_depth, brace_height, :walnut_plywood)
      ] })
    end

    # Backs retain their Y position and extend into the surrounding panels.
    def fit_carcass_back(assembly)
      name = assembly[:name]
      items = assembly[:parts]
      back = items.find { |item| item[:name] == "#{name} back" }
      depth = 0.25
      panels = [
        [items.find { |p| ["#{name} left side", "#{name} side 1"].include?(p[:name]) }, :x, :high],
        [items.find { |p| ["#{name} right side", "#{name} side 2"].include?(p[:name]) }, :x, :low],
        [items.find { |p| ["#{name} top", "#{name} top cap"].include?(p[:name]) }, :z, :low],
        [items.find { |p| p[:name] == "#{name} bottom" }, :z, :high]
      ]
      panels.each do |panel, axis, edge|
        next unless panel

        panel[:dado] = { axis: axis, slot_axis: :y, edge: edge, depth: depth,
                         bottom: back[:origin][1] - panel[:origin][1], height: back[:size][1] }
        index = axis == :x ? 0 : 2
        back[:origin][index] -= depth if edge == :high
        back[:size][index] += depth
      end
      assembly
    end

    # Drawer fronts share the opening's inset reveals; boxes allow 1/2 inch
    # on each side for slides. All dimensions are finished inches.
    def drawer_parts(name, x, y, z, opening_width, front_height, front_name: "#{name} front", box_depth: 12.0)
      reveal = 0.125
      front_thickness = layout[:walnut_front_thickness]
      box_x = x + 0.5
      box_y = y + front_thickness
      box_z = z + 0.5
      box_width = opening_width - 1.0
      box_height = front_height - 1.0
      wall = 0.5
      bottom = 0.5
      bottom_inset = 0.25
      groove = { depth: wall - bottom_inset, bottom: 0.5, height: bottom }
      items = [
        part(front_name, x + reveal, y, z,
             opening_width - 2 * reveal, front_thickness, front_height, :walnut_solid),
        part("#{name} bottom", box_x + bottom_inset, box_y + bottom_inset, box_z + groove[:bottom],
             box_width - 2 * bottom_inset, box_depth - 2 * bottom_inset, bottom, :baltic_birch_plywood).merge(drawer_box_role: :bottom)
      ]
      [box_x, box_x + box_width - wall].each_with_index do |side_x, index|
        items << part("#{name} side #{index + 1}", side_x, box_y, box_z,
                      wall, box_depth, box_height, :baltic_birch_plywood).merge(
                        drawer_box_role: :side, dado: groove.merge(axis: :x, edge: index.zero? ? :high : :low))
      end
      [box_y, box_y + box_depth - wall].each_with_index do |end_y, index|
        items << part("#{name} end #{index + 1}", box_x + wall, end_y, box_z,
                      box_width - 2 * wall, wall, box_height, :baltic_birch_plywood).merge(
                        drawer_box_role: :end, dado: groove.merge(axis: :y, edge: index.zero? ? :high : :low))
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
                                            15 - 2 * t, front_height, box_depth: 21.0))
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
      # Half-inch installation clearance above boxes; user-supplied trim closes it.
      top = s[:cabinet_height] - 0.5
      modules = []
      desk = carcass('D1 Desk lower surround', 0, 0, desk_width, 48.75,
                     bottom: false)
      modules << desk
      modules << desk_pedestal
      # D1's top is desk shelf 1. D3 has no bottom, avoiding a doubled shelf.
      # Both shelves span the full opening; there is no center divider.
      modules << carcass('D3 Desk full-width upper', 0, 48.75, desk_width, top - 48.75,
                         bottom: false, shelves: [72])
      nightstand = carcass('N1 Nightstand drawers', tower_x, 0, s[:tower_width], 28.75)
      nightstand[:parts].concat(nightstand_drawer_parts)
      modules << nightstand
      # N1 supplies the base; exactly three shelves above the nightstand.
      modules << carcass('N2 Nightstand open shelves', tower_x, 28.75, s[:tower_width], top - 28.75,
                         bottom: false, shelves: [45, 61.5, 78])
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
        part('Desk top', t, -24, 29.25, desk_width - 2 * t, 24 - s[:back_recess] - s[:back_thickness], 1.5, :walnut_solid),
        led_strip('Desk LED', 2.5, 48.0, 42),
        led_strip('Nightstand LED', tower_x + 1.5, 45.0, s[:tower_width] - 3)
      ]
      modules.concat(headboard_carcasses)
      modules << { name: 'I1 Site-installed top, trim and lighting', shop_built: false, parts: loose }
      desktop = loose.find { |item| item[:name] == 'Desk top' }
      support_x = desktop[:origin][0] + desktop[:size][0] - t
      support_y = desktop[:origin][1] + s[:face_frame_thickness]
      support_height = desktop[:origin][2]
      modules << { name: 'D5 Desk right support panel', shop_built: true, parts: [
        part('Desk right walnut plywood support', support_x, support_y, 0,
             t, desktop[:size][1] - s[:face_frame_thickness], support_height, :walnut_plywood, grain: :z),
        part('Desk right support purpleheart face frame', support_x, support_y - s[:face_frame_thickness], 0,
             t, s[:face_frame_thickness], support_height, :purpleheart_solid, grain: :z)
      ] }
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
      continuous_horizontal_face_frame(modules, 'Desk top', t, desk_width - t,
                                       top - t, height: t, stile_edge: :top)
      bed_left = s[:filler_width] + s[:desk_width] + t
      continuous_horizontal_face_frame(modules, 'Bed', bed_left, bed_left + s[:bed_width] - 2 * t, 71.25)
      continuous_horizontal_face_frame(modules, 'Bed top', bed_left, bed_left + s[:bed_width] - 2 * t,
                                       top - t, height: t, stile_edge: :top)
      continuous_outer_face_frames(modules)
      name_purpleheart_parts(modules)
      share_drawer_box_components(modules)
    end

    # Geometry is local to the definition; placement and labels belong to instances.
    def component_signature(item)
      item.values_at(:size, :material, :grain, :taper_inset, :dado)
    end

    def share_drawer_box_components(modules)
      definitions = {}
      counts = Hash.new(0)
      modules.flat_map { |assembly| assembly[:parts] }.each do |item|
        role = item[:drawer_box_role]
        next unless role

        # Match local dimensions and grain, since instances use translation only.
        key = component_signature(item)
        item[:definition_name] = definitions[key] ||= begin
          counts[role] += 1
          "Drawer box #{role} #{counts[role]}"
        end
      end
      modules
    end

    # Consolidation uses coordinate labels internally; give finished parts clean,
    # unique names so separate frame pieces retain separate definitions.
    def name_purpleheart_parts(modules)
      frames = modules.flat_map { |assembly| assembly[:parts] }
                      .select { |item| item[:material] == :purpleheart_solid }
      frames.group_by { |item| item[:name].sub(/ [xz]-?\d.*\z/, '') }.each do |name, items|
        items.each_with_index do |item, index|
          item[:name] = items.length == 1 ? name : "#{name} #{index + 1}"
        end
      end
      modules
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
                             s[:panel_thickness], s[:face_frame_thickness], height, :purpleheart_solid, grain: :z)
      shared[:parts] << part('Far right continuous purpleheart stile', s[:wall_width] - s[:panel_thickness], front, 0,
                             s[:panel_thickness], s[:face_frame_thickness], height, :purpleheart_solid, grain: :z)
      modules
    end

    def continuous_desk_face_frame(modules)
      left = layout[:panel_thickness]
      right = layout[:filler_width] + layout[:desk_width] - layout[:panel_thickness]
      continuous_horizontal_face_frame(modules, 'Desk', left, right, 48.0, height: layout[:panel_thickness])
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
      model.start_operation('Rebuild Myri Built-in 2', true)
      operation_open = true

      previous_model_existed = remove_previous_model(model)
      materials = create_materials(model)
      root = model.entities.add_group
      root.name = 'Myri Built-in 2'
      root.set_attribute('MyriBuiltin2', 'generated_root', true)

      definitions = {}
      plan.each do |assembly|
        add_assembly(model, root.entities, materials, assembly, definitions)
      end
      add_led_illumination(model, root.entities, planned_parts) if layout[:show_led_illumination]
      add_myri_figure(root.entities, planned_parts.find { |item| item[:name] == 'Full mattress' })

      model.commit_operation
      operation_open = false
      model.active_view.zoom_extents unless previous_model_existed
      message = "Myri Built-in 2 rebuilt: #{planned_parts.length} components"
      Sketchup.status_text = message
      puts(message)
      root
    rescue StandardError => error
      model.abort_operation if model && operation_open
      warn("Myri Built-in 2 error: #{error.message}")
      warn(error.backtrace.join("\n"))
      raise
    end

    def validate_parts!(items)
      names = {}
      items.each do |item|
        name = item[:name]
        previous = names[name]
        shared_instance = previous && item[:definition_name] &&
                          previous[:definition_name] == item[:definition_name] &&
                          component_signature(previous) == component_signature(item)
        raise ArgumentError, "Duplicate part name: #{name}" if previous && !shared_instance

        names[name] = item
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

    # A translucent back-panel wash is a visual guide, not a lighting simulation.
    # Loose faces in a separate group keep the preview out of component cut lists.
    def add_led_illumination(model, entities, parts)
      preview = entities.add_group
      preview.name = 'LED illumination preview - hide to disable'
      preview.casts_shadows = false
      preview.receives_shadows = false
      back_y = -layout[:back_recess] - layout[:back_thickness] - 0.02
      bands = 12
      materials = bands.times.map do |index|
        name = "Myri LED wash #{index + 1}"
        material = model.materials[name] || model.materials.add(name)
        material.color = Sketchup::Color.new(255, 220, 150)
        material.alpha = 0.32 * (1.0 - index.to_f / bands)**2
        material
      end
      parts.select { |item| item[:material] == :led }.each do |strip|
        x, _, top = strip[:origin]
        width = strip[:size][0]
        bands.times do |index|
          z_top = top - 10.0 * index / bands
          z_bottom = top - 10.0 * (index + 1) / bands
          points = [[x, back_y, z_top], [x + width, back_y, z_top],
                    [x + width, back_y, z_bottom], [x, back_y, z_bottom]]
          face = preview.entities.add_face(points.map { |point| point.map(&:inch) })
          face.material = materials[index]
          face.back_material = materials[index]
          face.casts_shadows = false
          face.receives_shadows = false
        end
      end
      preview.entities.grep(Sketchup::Edge).each { |edge| edge.hidden = true }
      preview
    end

    def add_assembly(model, entities, materials, assembly, definitions)
      group = entities.add_group
      group.name = assembly[:name]
      group.set_attribute('MyriBuiltin2', 'shop_built', assembly[:shop_built])
      origin = 3.times.map { |axis| assembly[:parts].map { |item| item[:origin][axis] }.min }
      assembly[:parts].each do |item|
        local_origin = 3.times.map { |axis| item[:origin][axis] - origin[axis] }
        add_component(model, group.entities, materials, item.merge(origin: local_origin), definitions)
      end
      group.transform!(Geom::Transformation.translation(origin))
      group
    end

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
      figure.set_attribute('MyriBuiltin2', 'standing_height_in', s[:person_standing_height])
      figure.set_attribute('MyriBuiltin2', 'kneeling_height_in', kneeling_height)
      figure
    end

    def remove_previous_model(model)
      previous_groups = model.entities.grep(Sketchup::Group).select do |group|
        generated = group.get_attribute('MyriBuiltin2', 'generated_root', false)
        generated || group.name == 'Myri Built-in 2'
      end
      previous_groups.each(&:erase!)
      !previous_groups.empty?
    end

    def create_materials(model)
      textures = wood_textures
      types = material_types
      thicknesses = material_stock_thicknesses
      material_palette.each_with_object({}) do |(key, rgb), collection|
        name = key.to_s.split('_').map(&:capitalize).join(' ')
        material = model.materials[name] || model.materials.add(name)
        material.set_attribute('ladb_opencutlist', 'type', types[key]) if types.key?(key)
        if thicknesses.key?(key)
          existing = material.get_attribute('ladb_opencutlist', 'std_thicknesses', '').to_s.split(';')
          stock = (existing.map(&:strip).reject(&:empty?) + thicknesses[key]).uniq
          material.set_attribute('ladb_opencutlist', 'std_thicknesses', stock.join(';'))
        end
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

    def add_component(model, parent_entities, materials, part_data, definitions = {})
      definition_name = part_data.fetch(:definition_name, part_data[:name])
      definition = definitions[definition_name] ||= create_part_definition(model, materials, part_data, definition_name)
      transform = Geom::Transformation.translation(part_data[:origin].map(&:inch))
      instance = parent_entities.add_instance(definition, transform)
      instance.name = definition_name
      instance.material = materials.fetch(part_data[:material])
      instance
    end

    def create_part_definition(model, materials, part_data, name)
      definition = model.definitions["MyriBuiltin2 - #{name}"] || model.definitions.add("MyriBuiltin2 - #{name}")
      definition.entities.clear!
      width, depth, height = part_data[:size]
      if part_data[:dado]
        add_dado_panel(definition.entities, part_data[:size], part_data[:dado])
      elsif part_data[:taper_inset]
        add_tapered_leg(definition.entities, width, depth, height, part_data[:taper_inset])
      else
        add_box(definition.entities, width, depth, height)
      end
      paint_part_faces(definition.entities, materials.fetch(part_data[:material]), part_data)
      definition.set_attribute('MyriBuiltin2', 'generated_part', true)
      %w[width_in depth_in height_in].zip(part_data[:size]).each do |key, value|
        definition.set_attribute('MyriBuiltin2', key, value)
      end
      definition
    end

    def paint_part_faces(entities, material, part_data)
      if material.texture
        texture_settings = wood_textures.fetch(part_data[:material])
        axes = { x: Geom::Vector3d.new(1, 0, 0),
                 y: Geom::Vector3d.new(0, 1, 0),
                 z: Geom::Vector3d.new(0, 0, 1) }
      end
      entities.grep(Sketchup::Face).each do |face|
        face.material = material
        position_wood_texture(face, material, part_data, texture_settings, axes) if material.texture
      end
    end

    # Extrude a notched profile so the groove is real geometry on the inside face.
    def add_dado_panel(entities, size, dado)
      axes = [:x, :y, :z]
      thickness_axis = axes.index(dado[:axis])
      slot_axis = axes.index(dado.fetch(:slot_axis, :z))
      length_axis = ([0, 1, 2] - [thickness_axis, slot_axis]).first
      thickness = size[thickness_axis]
      span = size[slot_axis]
      length = size[length_axis]
      low = dado[:bottom]
      high = low + dado[:height]
      profile = [[0, 0], [thickness, 0], [thickness, low],
                 [thickness - dado[:depth], low], [thickness - dado[:depth], high],
                 [thickness, high], [thickness, span], [0, span]]
      points = profile.map do |across, along|
        across = thickness - across if dado[:edge] == :low
        point = [0, 0, 0]
        point[thickness_axis] = across
        point[slot_axis] = along
        point.map(&:inch)
      end
      face = entities.add_face(points)
      normal = face.normal.public_send(axes[length_axis])
      face.reverse! if normal.negative?
      face.pushpull(length.inch)
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

MyriBuiltin2.build
