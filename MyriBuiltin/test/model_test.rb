# frozen_string_literal: true

require 'minitest/autorun'
require 'json'
require 'digest'

# Exercise the pure model description without invoking SketchUp's renderer.
script = File.expand_path('../MyriBuiltin.rb', __dir__)
eval(File.read(script).sub(/MyriBuiltin.build\s*\z/, ''), TOPLEVEL_BINDING, script)

class ModelTest < Minitest::Test
  def setup
    @plan = MyriBuiltin.assemblies
    @parts = @plan.flat_map { |assembly| assembly[:parts] }
  end

  def test_current_design_snapshot
    signature = @plan.map do |assembly|
      [assembly[:name], assembly[:shop_built], assembly[:parts].map do |part|
        [part[:name], part[:origin].map { |n| n.to_f.round(6) },
         part[:size].map { |n| n.to_f.round(6) }, part[:material], part[:grain], part[:taper_inset]]
      end]
    end
    # Reviewed design with a continuous desk/bed headers and outer stiles.
    assert_equal 'b838177c10b084bf7f8c33f4efd2e21f50dd6bce26597d62f6d0243cff7e83d7',
                 Digest::SHA256.hexdigest(JSON.generate(signature))
  end

  def test_desk_header_is_one_continuous_rail
    rail = @parts.find { |p| p[:name] == 'Desk continuous horizontal purpleheart face frame' }
    assert_equal [1.0, -13.75, 48.0], rail[:origin]
    assert_equal [43.875, 0.75, 1.5], rail[:size]
    refute @parts.any? { |p| p[:name] == 'D1 Desk lower surround top purpleheart frame z22.75-24.25' }
    stile = @parts.find { |p| p[:name] == 'Desk upper center purpleheart stile' }
    assert_equal 49.5, stile[:origin][2]
  end

  def test_outer_stiles_are_single_full_height_parts
    stiles = @parts.select do |p|
      p[:material] == :purpleheart_solid && p[:grain] == :z &&
        (p[:origin][0] == 0 || p[:origin][0] + p[:size][0] == 128)
    end
    assert_equal 2, stiles.size
    assert stiles.all? { |p| p[:origin][2] == 0 && p[:size][2] == 95.5 }
  end

  def test_bed_header_is_one_continuous_rail
    rail = @parts.find { |p| p[:name] == 'Bed continuous horizontal purpleheart face frame' }
    assert_equal [46.375, -13.75, 71.25], rail[:origin]
    assert_equal [57.25, 0.75, 1.5], rail[:size]
    stiles = @parts.select { |p| p[:name].start_with?('Bed bridge purpleheart stile') }
    assert_equal 2, stiles.size
    assert stiles.all? { |p| p[:origin][2] == 72.75 }
  end

  def test_bridge_top_frame_is_continuous
    rail = @parts.find { |p| p[:name] == 'Bed top continuous horizontal purpleheart face frame' }
    assert_equal [46.375, -13.75, 94.75], rail[:origin]
    assert_equal [57.25, 0.75, 0.75], rail[:size]
    stiles = @parts.select { |p| p[:name].start_with?('Bed bridge purpleheart stile') }
    assert stiles.all? { |p| p[:origin][2] + p[:size][2] == 94.75 }
  end

  def test_desk_top_frame_is_continuous
    rail = @parts.find { |p| p[:name] == 'Desk top continuous horizontal purpleheart face frame' }
    assert_equal [1.0, -13.75, 94.75], rail[:origin]
    assert_equal [43.875, 0.75, 0.75], rail[:size]
    stile = @parts.find { |p| p[:name] == 'Desk upper center purpleheart stile' }
    assert_equal 94.75, stile[:origin][2] + stile[:size][2]
  end

  def test_regeneration_is_stable_and_does_not_share_mutable_parts
    assert_equal @plan, MyriBuiltin.assemblies
    @parts.first[:origin][0] = -1000
    refute_equal @plan, MyriBuiltin.assemblies
  end

  def test_all_parts_have_valid_geometry_and_unique_names
    MyriBuiltin.validate_parts!(@parts)
    assert_equal 173, @parts.size
    assert @parts.all? { |part| MyriBuiltin.material_palette.key?(part[:material]) }
  end

  def test_no_solid_parts_overlap
    @parts.combination(2) do |a, b|
      overlap = 3.times.all? do |axis|
        [a[:origin][axis] + a[:size][axis], b[:origin][axis] + b[:size][axis]].min -
          [a[:origin][axis], b[:origin][axis]].max > 0.00001
      end
      refute overlap, "Overlap: #{a[:name]} / #{b[:name]}"
    end
  end

  def test_zero_width_roundoff_is_rejected_with_a_part_name
    invalid = MyriBuiltin.part('Degenerate strip', 0, 0, 0, 1.4e-14, 0.75, 0.75, :purpleheart_solid)
    error = assert_raises(ArgumentError) { MyriBuiltin.validate_parts!([invalid]) }
    assert_includes error.message, 'Degenerate strip'
  end

  def test_bad_tapers_and_duplicate_names_are_rejected
    invalid = MyriBuiltin.part('Bad leg', 0, 0, 0, 3, 1.5, 8, :walnut_solid).merge(taper_inset: [2, 0.25])
    assert_raises(ArgumentError) { MyriBuiltin.validate_parts!([invalid]) }
    assert_raises(ArgumentError) { MyriBuiltin.validate_parts!([@parts.first, @parts.first]) }
  end
end
