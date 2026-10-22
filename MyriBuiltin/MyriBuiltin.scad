// Myri Built-in — full design snapshot from MyriBuiltin.py.
// All coordinates and dimensions are MILLIMETERS.
// X is right, negative Y projects into the room, Z is up.
// 147 parts in 17 assemblies. Dado grooves and tapered legs are solid geometry.
// Source wood photographs are represented by flat material palette colors.
// Photo figure and simulated light washes are absent from the source design.
// F5 previews material colors. This file requires no external files.
// Edits to the Fusion Python script do not automatically update this snapshot.

/* [Display] */
show_mattress = true;
show_lighting = true;
assembly = "All"; // [All,D1,D2,D3,N1,N2,B1,B2,B3,H1,I1,D5,F1,F2,F3,I2,I3,I4]
// Leave empty for all parts; otherwise use an exact part name from below.
part_name = "";

/* [Hidden] */
$fn = 32;
eps = 0.0254;

// Dado = [thickness axis, slot axis, high edge, depth, start, slot width].
module dado_panel(s, dado) {
    a = dado[0];
    b = dado[1];
    cut_origin = [for (i=[0:2])
        i==a ? (dado[2] ? s[i]-dado[3] : -eps) :
        i==b ? dado[4] : -eps];
    cut_size = [for (i=[0:2])
        i==a ? dado[3]+eps : i==b ? dado[5] : s[i]+2*eps];
    difference() {
        cube(s);
        translate(cut_origin) cube(cut_size);
    }
}

module tapered_leg(s, inset) {
    bottom = [s[0]-2*inset[0], s[1]-2*inset[1]];
    assert(bottom[0]>0 && bottom[1]>0, "Invalid tapered leg dimensions");
    translate([s[0]/2,s[1]/2,0])
        linear_extrude(height=s[2],scale=[s[0]/bottom[0],s[1]/bottom[1]])
            square(bottom,center=true);
}

module part(name, pos, s, rgb, taper=[], dado=[], mattress=false, lighting=false) {
    if ((part_name=="" || part_name==name) &&
        (!mattress || show_mattress) && (!lighting || show_lighting))
        color(rgb) translate(pos)
            if (len(taper)>0) tapered_leg(s,taper);
            else if (len(dado)>0) dado_panel(s,dado);
            else cube(s);
}

// D1 Desk lower surround; 5 parts; shop-built: true
module assembly_D1() {
    // Material: walnut_plywood; grain: z
    part("D1 Desk lower surround left side", [0.0,-330.2,0.0], [19.05,330.2,1238.25], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,true,6.35,304.8,6.35], false, false);
    // Material: walnut_plywood; grain: z
    part("D1 Desk lower surround right side", [1139.825,-330.2,0.0], [19.05,330.2,1238.25], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,false,6.35,304.8,6.35], false, false);
    // Material: walnut_plywood; grain: x
    part("D1 Desk lower surround top", [19.05,-330.2,1219.2], [1120.775,330.2,19.05], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [2,1,false,6.35,304.8,6.35], false, false);
    // Material: walnut_plywood; grain: z
    part("D1 Desk lower surround back", [12.7,-25.4,0.0], [1133.475,6.35,1225.55], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], false, false);
    // Material: walnut_plywood; grain: x
    part("D1 Desk lower surround top mounting brace", [19.05,-19.05,1143.0], [1120.775,19.05,76.2], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], false, false);
}

// D2 Desk drawer pedestal; 28 parts; shop-built: true
module assembly_D2() {
    // Material: walnut_plywood; grain: z
    part("D2 Desk drawer pedestal left side", [25.4,-584.2,0.0], [19.05,558.8,742.95], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,true,6.35,533.4,6.35], false, false);
    // Material: walnut_plywood; grain: z
    part("D2 Desk drawer pedestal right side", [387.35,-584.2,0.0], [19.05,558.8,742.95], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,false,6.35,533.4,6.35], false, false);
    // Material: walnut_plywood; grain: y
    part("D2 Desk drawer pedestal top", [44.45,-584.2,723.9], [342.9,558.8,19.05], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [2,1,false,6.35,533.4,6.35], false, false);
    // Material: walnut_plywood; grain: y
    part("D2 Desk drawer pedestal bottom", [44.45,-584.2,0.0], [342.9,558.8,19.05], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [2,1,true,6.35,533.4,6.35], false, false);
    // Material: walnut_plywood; grain: z
    part("D2 Desk drawer pedestal back", [38.1,-50.8,12.7], [355.6,6.35,717.55], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], false, false);
    // Material: walnut_plywood; grain: x
    part("D2 Desk drawer pedestal top mounting brace", [44.45,-44.45,647.7], [342.9,19.05,76.2], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], false, false);
    // Material: purpleheart_solid; grain: z
    part("Desk file drawer front", [47.625,-603.25,22.225], [336.55,19.05,347.6625], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
    // Material: baltic_birch_plywood; grain: y
    part("Desk file drawer bottom", [63.5,-577.85,47.625], [304.8,520.7,12.7], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [], false, false);
    // Material: baltic_birch_plywood; grain: y
    part("Desk file drawer side 1", [57.15,-584.2,34.925], [12.7,533.4,322.2625], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [0,2,true,6.35,12.7,12.7], false, false);
    // Material: baltic_birch_plywood; grain: y
    part("Desk file drawer side 2", [361.95,-584.2,34.925], [12.7,533.4,322.2625], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [0,2,false,6.35,12.7,12.7], false, false);
    // Material: baltic_birch_plywood; grain: z
    part("Desk file drawer end 1", [69.85,-584.2,34.925], [292.1,12.7,322.2625], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [1,2,true,6.35,12.7,12.7], false, false);
    // Material: baltic_birch_plywood; grain: z
    part("Desk file drawer end 2", [69.85,-63.5,34.925], [292.1,12.7,322.2625], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [1,2,false,6.35,12.7,12.7], false, false);
    // Material: purpleheart_solid; grain: x
    part("Desk drawer 2 front", [47.625,-603.25,373.0625], [336.55,19.05,172.24375], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
    // Material: baltic_birch_plywood; grain: y
    part("Desk drawer 2 bottom", [63.5,-577.85,398.4625], [304.8,520.7,12.7], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [], false, false);
    // Material: baltic_birch_plywood; grain: y
    part("Desk drawer 2 side 1", [57.15,-584.2,385.7625], [12.7,533.4,146.84375], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [0,2,true,6.35,12.7,12.7], false, false);
    // Material: baltic_birch_plywood; grain: y
    part("Desk drawer 2 side 2", [361.95,-584.2,385.7625], [12.7,533.4,146.84375], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [0,2,false,6.35,12.7,12.7], false, false);
    // Material: baltic_birch_plywood; grain: x
    part("Desk drawer 2 end 1", [69.85,-584.2,385.7625], [292.1,12.7,146.84375], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [1,2,true,6.35,12.7,12.7], false, false);
    // Material: baltic_birch_plywood; grain: x
    part("Desk drawer 2 end 2", [69.85,-63.5,385.7625], [292.1,12.7,146.84375], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [1,2,false,6.35,12.7,12.7], false, false);
    // Material: purpleheart_solid; grain: x
    part("Desk drawer 3 front", [47.625,-603.25,548.48125], [336.55,19.05,172.24375], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
    // Material: baltic_birch_plywood; grain: y
    part("Desk drawer 3 bottom", [63.5,-577.85,573.88125], [304.8,520.7,12.7], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [], false, false);
    // Material: baltic_birch_plywood; grain: y
    part("Desk drawer 3 side 1", [57.15,-584.2,561.18125], [12.7,533.4,146.84375], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [0,2,true,6.35,12.7,12.7], false, false);
    // Material: baltic_birch_plywood; grain: y
    part("Desk drawer 3 side 2", [361.95,-584.2,561.18125], [12.7,533.4,146.84375], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [0,2,false,6.35,12.7,12.7], false, false);
    // Material: baltic_birch_plywood; grain: x
    part("Desk drawer 3 end 1", [69.85,-584.2,561.18125], [292.1,12.7,146.84375], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [1,2,true,6.35,12.7,12.7], false, false);
    // Material: baltic_birch_plywood; grain: x
    part("Desk drawer 3 end 2", [69.85,-63.5,561.18125], [292.1,12.7,146.84375], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [1,2,false,6.35,12.7,12.7], false, false);
    // Material: purpleheart_solid; grain: z
    part("D2 Desk drawer pedestal left side purpleheart frame", [25.4,-603.25,0.0], [19.05,19.05,742.95], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
    // Material: purpleheart_solid; grain: z
    part("D2 Desk drawer pedestal right side purpleheart frame", [387.35,-603.25,0.0], [19.05,19.05,742.95], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
    // Material: purpleheart_solid; grain: x
    part("D2 Desk drawer pedestal bottom purpleheart frame", [44.45,-603.25,0.0], [342.9,19.05,19.05], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
    // Material: purpleheart_solid; grain: x
    part("D2 Desk drawer pedestal top purpleheart frame", [44.45,-603.25,723.9], [342.9,19.05,19.05], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
}

// D3 Desk full-width upper; 7 parts; shop-built: true
module assembly_D3() {
    // Material: walnut_plywood; grain: z
    part("D3 Desk full-width upper left side", [0.0,-330.2,1238.25], [19.05,330.2,1187.45], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,true,6.35,304.8,6.35], false, false);
    // Material: walnut_plywood; grain: z
    part("D3 Desk full-width upper right side", [1139.825,-330.2,1238.25], [19.05,330.2,1187.45], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,false,6.35,304.8,6.35], false, false);
    // Material: walnut_plywood; grain: x
    part("D3 Desk full-width upper top", [19.05,-330.2,2406.65], [1120.775,330.2,19.05], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [2,1,false,6.35,304.8,6.35], false, false);
    // Material: walnut_plywood; grain: x
    part("D3 Desk full-width upper shelf 1", [19.05,-330.2,1828.8], [1120.775,304.8,19.05], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], false, false);
    // Material: walnut_plywood; grain: z
    part("D3 Desk full-width upper back", [12.7,-25.4,1238.25], [1133.475,6.35,1174.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], false, false);
    // Material: walnut_plywood; grain: x
    part("D3 Desk full-width upper top mounting brace", [19.05,-19.05,2330.45], [1120.775,19.05,76.2], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], false, false);
    // Material: purpleheart_solid; grain: x
    part("D3 Desk full-width upper shelf 1 purpleheart frame", [19.05,-349.25,1828.8], [1120.775,19.05,19.05], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
}

// N1 Nightstand drawers; 26 parts; shop-built: true
module assembly_N1() {
    // Material: walnut_plywood; grain: z
    part("N1 Nightstand drawers left side", [2651.125,-330.2,0.0], [19.05,330.2,730.25], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,true,6.35,304.8,6.35], false, false);
    // Material: walnut_plywood; grain: z
    part("N1 Nightstand drawers right side", [3232.15,-330.2,0.0], [19.05,330.2,730.25], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,false,6.35,304.8,6.35], false, false);
    // Material: walnut_plywood; grain: x
    part("N1 Nightstand drawers top", [2670.175,-330.2,711.2], [561.975,330.2,19.05], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [2,1,false,6.35,304.8,6.35], false, false);
    // Material: walnut_plywood; grain: x
    part("N1 Nightstand drawers bottom", [2670.175,-330.2,0.0], [561.975,330.2,19.05], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [2,1,true,6.35,304.8,6.35], false, false);
    // Material: walnut_plywood; grain: z
    part("N1 Nightstand drawers back", [2663.825,-25.4,12.7], [574.675,6.35,704.85], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], false, false);
    // Material: walnut_plywood; grain: x
    part("N1 Nightstand drawers top mounting brace", [2670.175,-19.05,635.0], [561.975,19.05,76.2], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], false, false);
    // Material: purpleheart_solid; grain: x
    part("Nightstand drawer front 1", [2673.35,-349.25,22.225], [555.625,19.05,226.4833333333], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
    // Material: baltic_birch_plywood; grain: x
    part("Nightstand drawer 1 bottom", [2689.225,-323.85,47.625], [523.875,292.1,12.7], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [], false, false);
    // Material: baltic_birch_plywood; grain: y
    part("Nightstand drawer 1 side 1", [2682.875,-330.2,34.925], [12.7,304.8,201.0833333333], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [0,2,true,6.35,12.7,12.7], false, false);
    // Material: baltic_birch_plywood; grain: y
    part("Nightstand drawer 1 side 2", [3206.75,-330.2,34.925], [12.7,304.8,201.0833333333], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [0,2,false,6.35,12.7,12.7], false, false);
    // Material: baltic_birch_plywood; grain: x
    part("Nightstand drawer 1 end 1", [2695.575,-330.2,34.925], [511.175,12.7,201.0833333333], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [1,2,true,6.35,12.7,12.7], false, false);
    // Material: baltic_birch_plywood; grain: x
    part("Nightstand drawer 1 end 2", [2695.575,-38.1,34.925], [511.175,12.7,201.0833333333], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [1,2,false,6.35,12.7,12.7], false, false);
    // Material: purpleheart_solid; grain: x
    part("Nightstand drawer front 2", [2673.35,-349.25,251.8833333333], [555.625,19.05,226.4833333333], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
    // Material: baltic_birch_plywood; grain: x
    part("Nightstand drawer 2 bottom", [2689.225,-323.85,277.2833333333], [523.875,292.1,12.7], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [], false, false);
    // Material: baltic_birch_plywood; grain: y
    part("Nightstand drawer 2 side 1", [2682.875,-330.2,264.5833333333], [12.7,304.8,201.0833333333], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [0,2,true,6.35,12.7,12.7], false, false);
    // Material: baltic_birch_plywood; grain: y
    part("Nightstand drawer 2 side 2", [3206.75,-330.2,264.5833333333], [12.7,304.8,201.0833333333], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [0,2,false,6.35,12.7,12.7], false, false);
    // Material: baltic_birch_plywood; grain: x
    part("Nightstand drawer 2 end 1", [2695.575,-330.2,264.5833333333], [511.175,12.7,201.0833333333], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [1,2,true,6.35,12.7,12.7], false, false);
    // Material: baltic_birch_plywood; grain: x
    part("Nightstand drawer 2 end 2", [2695.575,-38.1,264.5833333333], [511.175,12.7,201.0833333333], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [1,2,false,6.35,12.7,12.7], false, false);
    // Material: purpleheart_solid; grain: x
    part("Nightstand drawer front 3", [2673.35,-349.25,481.5416666667], [555.625,19.05,226.4833333333], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
    // Material: baltic_birch_plywood; grain: x
    part("Nightstand drawer 3 bottom", [2689.225,-323.85,506.9416666667], [523.875,292.1,12.7], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [], false, false);
    // Material: baltic_birch_plywood; grain: y
    part("Nightstand drawer 3 side 1", [2682.875,-330.2,494.2416666667], [12.7,304.8,201.0833333333], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [0,2,true,6.35,12.7,12.7], false, false);
    // Material: baltic_birch_plywood; grain: y
    part("Nightstand drawer 3 side 2", [3206.75,-330.2,494.2416666667], [12.7,304.8,201.0833333333], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [0,2,false,6.35,12.7,12.7], false, false);
    // Material: baltic_birch_plywood; grain: x
    part("Nightstand drawer 3 end 1", [2695.575,-330.2,494.2416666667], [511.175,12.7,201.0833333333], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [1,2,true,6.35,12.7,12.7], false, false);
    // Material: baltic_birch_plywood; grain: x
    part("Nightstand drawer 3 end 2", [2695.575,-38.1,494.2416666667], [511.175,12.7,201.0833333333], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [1,2,false,6.35,12.7,12.7], false, false);
    // Material: purpleheart_solid; grain: x
    part("N1 Nightstand drawers bottom purpleheart frame", [2670.175,-349.25,0.0], [561.975,19.05,19.05], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
    // Material: purpleheart_solid; grain: x
    part("N1 Nightstand drawers top purpleheart frame", [2670.175,-349.25,711.2], [561.975,19.05,19.05], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
}

// N2 Nightstand open shelves; 12 parts; shop-built: true
module assembly_N2() {
    // Material: walnut_plywood; grain: z
    part("N2 Nightstand open shelves left side", [2651.125,-330.2,730.25], [19.05,330.2,1695.45], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,true,6.35,304.8,6.35], false, false);
    // Material: walnut_plywood; grain: z
    part("N2 Nightstand open shelves right side", [3232.15,-330.2,730.25], [19.05,330.2,1695.45], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,false,6.35,304.8,6.35], false, false);
    // Material: walnut_plywood; grain: x
    part("N2 Nightstand open shelves top", [2670.175,-330.2,2406.65], [561.975,330.2,19.05], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [2,1,false,6.35,304.8,6.35], false, false);
    // Material: walnut_plywood; grain: x
    part("N2 Nightstand open shelves shelf 1", [2670.175,-330.2,1143.0], [561.975,304.8,19.05], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], false, false);
    // Material: walnut_plywood; grain: x
    part("N2 Nightstand open shelves shelf 2", [2670.175,-330.2,1562.1], [561.975,304.8,19.05], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], false, false);
    // Material: walnut_plywood; grain: x
    part("N2 Nightstand open shelves shelf 3", [2670.175,-330.2,1981.2], [561.975,304.8,19.05], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], false, false);
    // Material: walnut_plywood; grain: z
    part("N2 Nightstand open shelves back", [2663.825,-25.4,730.25], [574.675,6.35,1682.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], false, false);
    // Material: walnut_plywood; grain: x
    part("N2 Nightstand open shelves top mounting brace", [2670.175,-19.05,2330.45], [561.975,19.05,76.2], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], false, false);
    // Material: purpleheart_solid; grain: x
    part("N2 Nightstand open shelves shelf 1 purpleheart frame", [2670.175,-349.25,1143.0], [561.975,19.05,19.05], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
    // Material: purpleheart_solid; grain: x
    part("N2 Nightstand open shelves shelf 2 purpleheart frame", [2670.175,-349.25,1562.1], [561.975,19.05,19.05], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
    // Material: purpleheart_solid; grain: x
    part("N2 Nightstand open shelves shelf 3 purpleheart frame", [2670.175,-349.25,1981.2], [561.975,19.05,19.05], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
    // Material: purpleheart_solid; grain: x
    part("N2 Nightstand open shelves top purpleheart frame", [2670.175,-349.25,2406.65], [561.975,19.05,19.05], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
}

// B1 Bridge cabinet; 7 parts; shop-built: true
module assembly_B1() {
    // Material: walnut_plywood; grain: z
    part("B1 Bridge cabinet left side", [1158.875,-330.2,1828.8], [19.05,330.2,596.9], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,true,6.35,304.8,6.35], false, false);
    // Material: walnut_plywood; grain: z
    part("B1 Bridge cabinet right side", [1637.2416666667,-330.2,1828.8], [19.05,330.2,596.9], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,false,6.35,304.8,6.35], false, false);
    // Material: walnut_plywood; grain: x
    part("B1 Bridge cabinet top", [1177.925,-330.2,2406.65], [459.3166666667,330.2,19.05], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [2,1,false,6.35,304.8,6.35], false, false);
    // Material: walnut_plywood; grain: x
    part("B1 Bridge cabinet bottom", [1177.925,-330.2,1828.8], [459.3166666667,330.2,19.05], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [2,1,true,6.35,304.8,6.35], false, false);
    // Material: walnut_plywood; grain: z
    part("B1 Bridge cabinet back", [1171.575,-25.4,1841.5], [472.0166666667,6.35,571.5], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], false, false);
    // Material: walnut_plywood; grain: x
    part("B1 Bridge cabinet top mounting brace", [1177.925,-19.05,2330.45], [459.3166666667,19.05,76.2], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], false, false);
    // Material: purpleheart_solid; grain: z
    part("Bridge door 1", [1181.1,-349.25,1851.025], [452.9666666667,19.05,552.45], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
}

// B2 Bridge cabinet; 7 parts; shop-built: true
module assembly_B2() {
    // Material: walnut_plywood; grain: z
    part("B2 Bridge cabinet left side", [1656.2916666667,-330.2,1828.8], [19.05,330.2,596.9], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,true,6.35,304.8,6.35], false, false);
    // Material: walnut_plywood; grain: z
    part("B2 Bridge cabinet right side", [2134.6583333333,-330.2,1828.8], [19.05,330.2,596.9], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,false,6.35,304.8,6.35], false, false);
    // Material: walnut_plywood; grain: x
    part("B2 Bridge cabinet top", [1675.3416666667,-330.2,2406.65], [459.3166666667,330.2,19.05], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [2,1,false,6.35,304.8,6.35], false, false);
    // Material: walnut_plywood; grain: x
    part("B2 Bridge cabinet bottom", [1675.3416666667,-330.2,1828.8], [459.3166666667,330.2,19.05], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [2,1,true,6.35,304.8,6.35], false, false);
    // Material: walnut_plywood; grain: z
    part("B2 Bridge cabinet back", [1668.9916666667,-25.4,1841.5], [472.0166666667,6.35,571.5], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], false, false);
    // Material: walnut_plywood; grain: x
    part("B2 Bridge cabinet top mounting brace", [1675.3416666667,-19.05,2330.45], [459.3166666667,19.05,76.2], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], false, false);
    // Material: purpleheart_solid; grain: z
    part("Bridge door 2", [1678.5166666667,-349.25,1851.025], [452.9666666667,19.05,552.45], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
}

// B3 Bridge cabinet; 7 parts; shop-built: true
module assembly_B3() {
    // Material: walnut_plywood; grain: z
    part("B3 Bridge cabinet left side", [2153.7083333333,-330.2,1828.8], [19.05,330.2,596.9], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,true,6.35,304.8,6.35], false, false);
    // Material: walnut_plywood; grain: z
    part("B3 Bridge cabinet right side", [2632.075,-330.2,1828.8], [19.05,330.2,596.9], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,false,6.35,304.8,6.35], false, false);
    // Material: walnut_plywood; grain: x
    part("B3 Bridge cabinet top", [2172.7583333333,-330.2,2406.65], [459.3166666667,330.2,19.05], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [2,1,false,6.35,304.8,6.35], false, false);
    // Material: walnut_plywood; grain: x
    part("B3 Bridge cabinet bottom", [2172.7583333333,-330.2,1828.8], [459.3166666667,330.2,19.05], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [2,1,true,6.35,304.8,6.35], false, false);
    // Material: walnut_plywood; grain: z
    part("B3 Bridge cabinet back", [2166.4083333333,-25.4,1841.5], [472.0166666667,6.35,571.5], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], false, false);
    // Material: walnut_plywood; grain: x
    part("B3 Bridge cabinet top mounting brace", [2172.7583333333,-19.05,2330.45], [459.3166666667,19.05,76.2], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], false, false);
    // Material: purpleheart_solid; grain: z
    part("Bridge door 3", [2175.9333333333,-349.25,1851.025], [452.9666666667,19.05,552.45], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
}

// H1 Open headboard carcass; 8 parts; shop-built: true
module assembly_H1() {
    // Material: walnut_plywood; grain: z
    part("H1 Open headboard carcass back", [1171.575,-25.4,12.7], [1466.85,6.35,1803.4], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], false, false);
    // Material: walnut_plywood; grain: x
    part("H1 Open headboard carcass top mounting brace", [1177.925,-19.05,1733.55], [1454.15,19.05,76.2], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], false, false);
    // Material: walnut_plywood; grain: x
    part("H1 Open headboard carcass top cap", [1158.875,-330.2,1809.75], [1492.25,330.2,19.05], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [2,1,false,6.35,304.8,6.35], false, false);
    // Material: walnut_plywood; grain: x
    part("H1 Open headboard carcass bottom", [1177.925,-330.2,0.0], [1454.15,330.2,19.05], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [2,1,true,6.35,304.8,6.35], false, false);
    // Material: purpleheart_solid; grain: x
    part("Headboard purpleheart bed attachment cross brace", [1177.925,-63.5,203.2], [1454.15,19.05,203.2], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
    // Material: walnut_plywood; grain: z
    part("H1 Open headboard carcass side 1", [1158.875,-330.2,0.0], [19.05,330.2,1809.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,true,6.35,304.8,6.35], false, false);
    // Material: walnut_plywood; grain: z
    part("H1 Open headboard carcass side 2", [2632.075,-330.2,0.0], [19.05,330.2,1809.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,false,6.35,304.8,6.35], false, false);
    // Material: purpleheart_solid; grain: x
    part("H1 Open headboard carcass purpleheart bottom frame", [1177.925,-349.25,0.0], [1454.15,19.05,19.05], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
}

// I1 Site-installed top, trim and lighting; 3 parts; shop-built: false
module assembly_I1() {
    // Material: walnut_solid; grain: x
    part("Desk top", [19.05,-609.6,742.95], [1120.775,584.2,38.1], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], false, false);
    // Material: led; grain: x
    part("Desk LED", [63.5,-54.61,1212.85], [1066.8,10.16,6.35], [1.0,0.6196078431372549,0.1803921568627451], [], [], false, true);
    // Material: led; grain: x
    part("Nightstand LED", [2689.225,-54.61,1136.65], [523.875,10.16,6.35], [1.0,0.6196078431372549,0.1803921568627451], [], [], false, true);
}

// D5 Desk right support panel; 2 parts; shop-built: true
module assembly_D5() {
    // Material: walnut_plywood; grain: z
    part("Desk right walnut plywood support", [1120.775,-590.55,0.0], [19.05,565.15,742.95], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], false, false);
    // Material: purpleheart_solid; grain: z
    part("Desk right support purpleheart face frame", [1120.775,-609.6,0.0], [19.05,19.05,742.95], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
}

// F1 Bed left rail and ledge; 2 parts; shop-built: true
module assembly_F1() {
    // Material: walnut_solid; grain: y
    part("Bed left rail", [1181.1,-1993.9,203.2], [38.1,1930.4,203.2], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], false, false);
    // Material: purpleheart_solid; grain: y
    part("Bed left slat ledge", [1219.2,-1993.9,361.95], [25.4,1892.3,19.05], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
}

// F2 Bed right rail and ledge; 2 parts; shop-built: true
module assembly_F2() {
    // Material: walnut_solid; grain: y
    part("Bed right rail", [2590.8,-1993.9,203.2], [38.1,1930.4,203.2], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], false, false);
    // Material: purpleheart_solid; grain: y
    part("Bed right slat ledge", [2565.4,-1993.9,361.95], [25.4,1892.3,19.05], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
}

// F3 Bed foot assembly; 3 parts; shop-built: true
module assembly_F3() {
    // Material: walnut_solid; grain: x
    part("Bed footboard", [1181.1,-2032.0,203.2], [1447.8,38.1,203.2], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], false, false);
    // Material: walnut_solid; grain: z
    part("Bed front left leg", [1181.1,-2032.0,0.0], [76.2,38.1,203.2], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [12.7,6.35], [], false, false);
    // Material: walnut_solid; grain: z
    part("Bed front right leg", [2552.7,-2032.0,0.0], [76.2,38.1,203.2], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [12.7,6.35], [], false, false);
}

// I2 Bed parts - assemble in room; 18 parts; shop-built: false
module assembly_I2() {
    // Material: walnut_solid; grain: x
    part("Bed head rail", [1219.2,-101.6,203.2], [1371.6,38.1,203.2], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], false, false);
    // Material: walnut_solid; grain: y
    part("Bed center slat ledge", [1885.95,-1993.9,355.6], [76.2,1892.3,38.1], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], false, false);
    // Material: linen; grain: y
    part("Full mattress", [1219.2,-1981.2,393.7], [1371.6,1905.0,254.0], [0.8901960784313725,0.8392156862745098,0.7411764705882353], [], [], true, false);
    // Material: led; grain: x
    part("Bed bridge LED", [1206.5,-54.61,1803.4], [1397.0,10.16,6.35], [1.0,0.6196078431372549,0.1803921568627451], [], [], false, true);
    // Material: maple_solid; grain: x
    part("Maple solid bed slat", [1219.2,-1993.9,381.0], [1371.6,88.9,12.7], [0.7098039215686275,0.592156862745098,0.4470588235294118], [], [], false, false);
    // Material: maple_solid; grain: x
    part("Maple solid bed slat", [1219.2,-1855.1769230769,381.0], [1371.6,88.9,12.7], [0.7098039215686275,0.592156862745098,0.4470588235294118], [], [], false, false);
    // Material: maple_solid; grain: x
    part("Maple solid bed slat", [1219.2,-1716.4538461538,381.0], [1371.6,88.9,12.7], [0.7098039215686275,0.592156862745098,0.4470588235294118], [], [], false, false);
    // Material: maple_solid; grain: x
    part("Maple solid bed slat", [1219.2,-1577.7307692308,381.0], [1371.6,88.9,12.7], [0.7098039215686275,0.592156862745098,0.4470588235294118], [], [], false, false);
    // Material: maple_solid; grain: x
    part("Maple solid bed slat", [1219.2,-1439.0076923077,381.0], [1371.6,88.9,12.7], [0.7098039215686275,0.592156862745098,0.4470588235294118], [], [], false, false);
    // Material: maple_solid; grain: x
    part("Maple solid bed slat", [1219.2,-1300.2846153846,381.0], [1371.6,88.9,12.7], [0.7098039215686275,0.592156862745098,0.4470588235294118], [], [], false, false);
    // Material: maple_solid; grain: x
    part("Maple solid bed slat", [1219.2,-1161.5615384615,381.0], [1371.6,88.9,12.7], [0.7098039215686275,0.592156862745098,0.4470588235294118], [], [], false, false);
    // Material: maple_solid; grain: x
    part("Maple solid bed slat", [1219.2,-1022.8384615385,381.0], [1371.6,88.9,12.7], [0.7098039215686275,0.592156862745098,0.4470588235294118], [], [], false, false);
    // Material: maple_solid; grain: x
    part("Maple solid bed slat", [1219.2,-884.1153846154,381.0], [1371.6,88.9,12.7], [0.7098039215686275,0.592156862745098,0.4470588235294118], [], [], false, false);
    // Material: maple_solid; grain: x
    part("Maple solid bed slat", [1219.2,-745.3923076923,381.0], [1371.6,88.9,12.7], [0.7098039215686275,0.592156862745098,0.4470588235294118], [], [], false, false);
    // Material: maple_solid; grain: x
    part("Maple solid bed slat", [1219.2,-606.6692307692,381.0], [1371.6,88.9,12.7], [0.7098039215686275,0.592156862745098,0.4470588235294118], [], [], false, false);
    // Material: maple_solid; grain: x
    part("Maple solid bed slat", [1219.2,-467.9461538462,381.0], [1371.6,88.9,12.7], [0.7098039215686275,0.592156862745098,0.4470588235294118], [], [], false, false);
    // Material: maple_solid; grain: x
    part("Maple solid bed slat", [1219.2,-329.2230769231,381.0], [1371.6,88.9,12.7], [0.7098039215686275,0.592156862745098,0.4470588235294118], [], [], false, false);
    // Material: maple_solid; grain: x
    part("Maple solid bed slat", [1219.2,-190.5,381.0], [1371.6,88.9,12.7], [0.7098039215686275,0.592156862745098,0.4470588235294118], [], [], false, false);
}

// I3 Shared face frames - fit after installation; 6 parts; shop-built: false
module assembly_I3() {
    // Material: purpleheart_solid; grain: z
    part("Shared purpleheart stile 1", [1139.825,-349.25,0.0], [38.1,19.05,2425.7], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
    // Material: purpleheart_solid; grain: z
    part("Shared purpleheart stile 2", [2632.075,-349.25,0.0], [38.1,19.05,2425.7], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
    // Material: purpleheart_solid; grain: z
    part("Bed bridge purpleheart stile 1", [1637.2416666667,-349.25,1847.85], [38.1,19.05,558.8], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
    // Material: purpleheart_solid; grain: z
    part("Bed bridge purpleheart stile 2", [2134.6583333333,-349.25,1847.85], [38.1,19.05,558.8], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
    // Material: purpleheart_solid; grain: z
    part("Far left continuous purpleheart stile", [0.0,-349.25,0.0], [19.05,19.05,2425.7], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
    // Material: purpleheart_solid; grain: z
    part("Far right continuous purpleheart stile", [3232.15,-349.25,0.0], [19.05,19.05,2425.7], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
}

// I4 Shared horizontal face frames - fit after installation; 4 parts; shop-built: false
module assembly_I4() {
    // Material: purpleheart_solid; grain: x
    part("Desk continuous horizontal purpleheart face frame", [19.05,-349.25,1219.2], [1120.775,19.05,19.05], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
    // Material: purpleheart_solid; grain: x
    part("Desk top continuous horizontal purpleheart face frame", [19.05,-349.25,2406.65], [1120.775,19.05,19.05], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
    // Material: purpleheart_solid; grain: x
    part("Bed continuous horizontal purpleheart face frame", [1177.925,-349.25,1809.75], [1454.15,19.05,38.1], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
    // Material: purpleheart_solid; grain: x
    part("Bed top continuous horizontal purpleheart face frame", [1177.925,-349.25,2406.65], [1454.15,19.05,19.05], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], false, false);
}

if (assembly=="All" || assembly=="D1") assembly_D1();
if (assembly=="All" || assembly=="D2") assembly_D2();
if (assembly=="All" || assembly=="D3") assembly_D3();
if (assembly=="All" || assembly=="N1") assembly_N1();
if (assembly=="All" || assembly=="N2") assembly_N2();
if (assembly=="All" || assembly=="B1") assembly_B1();
if (assembly=="All" || assembly=="B2") assembly_B2();
if (assembly=="All" || assembly=="B3") assembly_B3();
if (assembly=="All" || assembly=="H1") assembly_H1();
if (assembly=="All" || assembly=="I1") assembly_I1();
if (assembly=="All" || assembly=="D5") assembly_D5();
if (assembly=="All" || assembly=="F1") assembly_F1();
if (assembly=="All" || assembly=="F2") assembly_F2();
if (assembly=="All" || assembly=="F3") assembly_F3();
if (assembly=="All" || assembly=="I2") assembly_I2();
if (assembly=="All" || assembly=="I3") assembly_I3();
if (assembly=="All" || assembly=="I4") assembly_I4();
