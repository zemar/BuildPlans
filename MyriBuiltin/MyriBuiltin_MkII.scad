// Myri built-in: standalone conversion of MyriBuiltin_MkII.rb.
// All part positions and dimensions below are INCHES; output defaults to mm.
// X runs left to right, negative Y projects into the room, Z points up.
// Includes 147 parts in 17 assemblies, with source dado geometry.
// Snapshot of the Ruby design: edits to the Ruby file do not update this file.
// Wood textures, the photo figure, and simulated light washes are omitted.
// F5: preview with material colors. F6: render solid geometry.

/* [Display] */
show_mattress = true;
show_lighting = true;
// All, or assembly prefix such as D1, H1, F3, I2.
assembly = "All";
// 25.4 produces millimeters; 1 produces inch-sized model coordinates.
unit_scale = 25.4;

/* [Hidden] */
$fn = 32;
eps = 0.001;

// Taper expands about the leg center, leaving its top at the source bounds.
module leg(s, inset) {
    translate([s[0]/2, s[1]/2, 0])
        linear_extrude(height=s[2], scale=[s[0]/(s[0]-2*inset[0]), s[1]/(s[1]-2*inset[1])])
            square([s[0]-2*inset[0], s[1]-2*inset[1]], center=true);
}

// Dado: [thickness axis, slot axis, high edge, depth, slot start, slot width].
module panel(s, dado) {
    a = dado[0]; b = dado[1];
    cut_origin = [for (i=[0:2]) i==a ? (dado[2] ? s[i]-dado[3] : -eps) : i==b ? dado[4] : -eps];
    cut_size = [for (i=[0:2]) i==a ? dado[3]+eps : i==b ? dado[5] : s[i]+2*eps];
    difference() {
        cube(s);
        translate(cut_origin) cube(cut_size);
    }
}

module part(pos, s, rgb, taper=[], dado=[], radius=0, mattress=false, lighting=false) {
    if ((!mattress || show_mattress) && (!lighting || show_lighting))
        color(rgb) translate(pos)
            if (radius > 0)
                linear_extrude(height=s[2])
                    translate([radius, radius])
                        offset(r=radius) square([s[0]-2*radius, s[1]-2*radius]);
            else if (len(dado)>0) panel(s, dado);
            else if (len(taper)>0) leg(s, taper);
            else cube(s);
}

// D1 Desk lower surround
module assembly_D1() {
    // D1 Desk lower surround left side (walnut_plywood)
    part([0,-13.0,0], [0.75,13.0,48.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,true,0.25,12.0,0.25], 0, false, false);
    // D1 Desk lower surround right side (walnut_plywood)
    part([44.875,-13.0,0], [0.75,13.0,48.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,false,0.25,12.0,0.25], 0, false, false);
    // D1 Desk lower surround top (walnut_plywood)
    part([0.75,-13.0,48.0], [44.125,13.0,0.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [2,1,false,0.25,12.0,0.25], 0, false, false);
    // D1 Desk lower surround back (walnut_plywood)
    part([0.5,-1.0,0], [44.625,0.25,48.25], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // D1 Desk lower surround top mounting brace (walnut_plywood)
    part([0.75,-0.75,45.0], [44.125,0.75,3.0], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
}

// D2 Desk drawer pedestal
module assembly_D2() {
    // D2 Desk drawer pedestal left side (walnut_plywood)
    part([1,-23.0,0], [0.75,22,29.25], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,true,0.25,21.0,0.25], 0, false, false);
    // D2 Desk drawer pedestal right side (walnut_plywood)
    part([15.25,-23.0,0], [0.75,22,29.25], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,false,0.25,21.0,0.25], 0, false, false);
    // D2 Desk drawer pedestal top (walnut_plywood)
    part([1.75,-23.0,28.5], [13.5,22,0.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [2,1,false,0.25,21.0,0.25], 0, false, false);
    // D2 Desk drawer pedestal bottom (walnut_plywood)
    part([1.75,-23.0,0], [13.5,22,0.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [2,1,true,0.25,21.0,0.25], 0, false, false);
    // D2 Desk drawer pedestal back (walnut_plywood)
    part([1.5,-2.0,0.5], [14.0,0.25,28.25], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // D2 Desk drawer pedestal top mounting brace (walnut_plywood)
    part([1.75,-1.75,25.5], [13.5,0.75,3.0], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // Desk file drawer front (walnut_solid)
    part([1.875,-23.75,0.875], [13.25,0.75,13.6875], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // Desk file drawer bottom (baltic_birch_plywood)
    part([2.5,-22.75,1.875], [12.0,20.5,0.5], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [], 0, false, false);
    // Desk file drawer side 1 (baltic_birch_plywood)
    part([2.25,-23.0,1.375], [0.5,21.0,12.6875], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [0,2,true,0.25,0.5,0.5], 0, false, false);
    // Desk file drawer side 2 (baltic_birch_plywood)
    part([14.25,-23.0,1.375], [0.5,21.0,12.6875], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [0,2,false,0.25,0.5,0.5], 0, false, false);
    // Desk file drawer end 1 (baltic_birch_plywood)
    part([2.75,-23.0,1.375], [11.5,0.5,12.6875], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [1,2,true,0.25,0.5,0.5], 0, false, false);
    // Desk file drawer end 2 (baltic_birch_plywood)
    part([2.75,-2.5,1.375], [11.5,0.5,12.6875], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [1,2,false,0.25,0.5,0.5], 0, false, false);
    // Desk drawer 2 front (walnut_solid)
    part([1.875,-23.75,14.6875], [13.25,0.75,6.78125], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // Desk drawer 2 bottom (baltic_birch_plywood)
    part([2.5,-22.75,15.6875], [12.0,20.5,0.5], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [], 0, false, false);
    // Desk drawer 2 side 1 (baltic_birch_plywood)
    part([2.25,-23.0,15.1875], [0.5,21.0,5.78125], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [0,2,true,0.25,0.5,0.5], 0, false, false);
    // Desk drawer 2 side 2 (baltic_birch_plywood)
    part([14.25,-23.0,15.1875], [0.5,21.0,5.78125], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [0,2,false,0.25,0.5,0.5], 0, false, false);
    // Desk drawer 2 end 1 (baltic_birch_plywood)
    part([2.75,-23.0,15.1875], [11.5,0.5,5.78125], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [1,2,true,0.25,0.5,0.5], 0, false, false);
    // Desk drawer 2 end 2 (baltic_birch_plywood)
    part([2.75,-2.5,15.1875], [11.5,0.5,5.78125], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [1,2,false,0.25,0.5,0.5], 0, false, false);
    // Desk drawer 3 front (walnut_solid)
    part([1.875,-23.75,21.59375], [13.25,0.75,6.78125], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // Desk drawer 3 bottom (baltic_birch_plywood)
    part([2.5,-22.75,22.59375], [12.0,20.5,0.5], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [], 0, false, false);
    // Desk drawer 3 side 1 (baltic_birch_plywood)
    part([2.25,-23.0,22.09375], [0.5,21.0,5.78125], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [0,2,true,0.25,0.5,0.5], 0, false, false);
    // Desk drawer 3 side 2 (baltic_birch_plywood)
    part([14.25,-23.0,22.09375], [0.5,21.0,5.78125], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [0,2,false,0.25,0.5,0.5], 0, false, false);
    // Desk drawer 3 end 1 (baltic_birch_plywood)
    part([2.75,-23.0,22.09375], [11.5,0.5,5.78125], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [1,2,true,0.25,0.5,0.5], 0, false, false);
    // Desk drawer 3 end 2 (baltic_birch_plywood)
    part([2.75,-2.5,22.09375], [11.5,0.5,5.78125], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [1,2,false,0.25,0.5,0.5], 0, false, false);
    // D2 Desk drawer pedestal left side purpleheart frame (purpleheart_solid)
    part([1,-23.75,0.0], [0.75,0.75,29.25], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], 0, false, false);
    // D2 Desk drawer pedestal right side purpleheart frame (purpleheart_solid)
    part([15.25,-23.75,0.0], [0.75,0.75,29.25], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], 0, false, false);
    // D2 Desk drawer pedestal bottom purpleheart frame (purpleheart_solid)
    part([1.75,-23.75,0], [13.5,0.75,0.75], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], 0, false, false);
    // D2 Desk drawer pedestal top purpleheart frame (purpleheart_solid)
    part([1.75,-23.75,28.5], [13.5,0.75,0.75], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], 0, false, false);
}

// D3 Desk full-width upper
module assembly_D3() {
    // D3 Desk full-width upper left side (walnut_plywood)
    part([0,-13.0,48.75], [0.75,13.0,46.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,true,0.25,12.0,0.25], 0, false, false);
    // D3 Desk full-width upper right side (walnut_plywood)
    part([44.875,-13.0,48.75], [0.75,13.0,46.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,false,0.25,12.0,0.25], 0, false, false);
    // D3 Desk full-width upper top (walnut_plywood)
    part([0.75,-13.0,94.75], [44.125,13.0,0.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [2,1,false,0.25,12.0,0.25], 0, false, false);
    // D3 Desk full-width upper shelf 1 (walnut_plywood)
    part([0.75,-13.0,72], [44.125,12.0,0.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // D3 Desk full-width upper back (walnut_plywood)
    part([0.5,-1.0,48.75], [44.625,0.25,46.25], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // D3 Desk full-width upper top mounting brace (walnut_plywood)
    part([0.75,-0.75,91.75], [44.125,0.75,3.0], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // D3 Desk full-width upper shelf 1 purpleheart frame (purpleheart_solid)
    part([0.75,-13.75,72], [44.125,0.75,0.75], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], 0, false, false);
}

// N1 Nightstand drawers
module assembly_N1() {
    // N1 Nightstand drawers left side (walnut_plywood)
    part([104.375,-13.0,0], [0.75,13.0,28.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,true,0.25,12.0,0.25], 0, false, false);
    // N1 Nightstand drawers right side (walnut_plywood)
    part([127.25,-13.0,0], [0.75,13.0,28.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,false,0.25,12.0,0.25], 0, false, false);
    // N1 Nightstand drawers top (walnut_plywood)
    part([105.125,-13.0,28.0], [22.125,13.0,0.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [2,1,false,0.25,12.0,0.25], 0, false, false);
    // N1 Nightstand drawers bottom (walnut_plywood)
    part([105.125,-13.0,0], [22.125,13.0,0.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [2,1,true,0.25,12.0,0.25], 0, false, false);
    // N1 Nightstand drawers back (walnut_plywood)
    part([104.875,-1.0,0.5], [22.625,0.25,27.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // N1 Nightstand drawers top mounting brace (walnut_plywood)
    part([105.125,-0.75,25.0], [22.125,0.75,3.0], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // Nightstand drawer front 1 (walnut_solid)
    part([105.25,-13.75,0.875], [21.875,0.75,8.916666666666666], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // Nightstand drawer 1 bottom (baltic_birch_plywood)
    part([105.875,-12.75,1.875], [20.625,11.5,0.5], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [], 0, false, false);
    // Nightstand drawer 1 side 1 (baltic_birch_plywood)
    part([105.625,-13.0,1.375], [0.5,12.0,7.916666666666666], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [0,2,true,0.25,0.5,0.5], 0, false, false);
    // Nightstand drawer 1 side 2 (baltic_birch_plywood)
    part([126.25,-13.0,1.375], [0.5,12.0,7.916666666666666], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [0,2,false,0.25,0.5,0.5], 0, false, false);
    // Nightstand drawer 1 end 1 (baltic_birch_plywood)
    part([106.125,-13.0,1.375], [20.125,0.5,7.916666666666666], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [1,2,true,0.25,0.5,0.5], 0, false, false);
    // Nightstand drawer 1 end 2 (baltic_birch_plywood)
    part([106.125,-1.5,1.375], [20.125,0.5,7.916666666666666], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [1,2,false,0.25,0.5,0.5], 0, false, false);
    // Nightstand drawer front 2 (walnut_solid)
    part([105.25,-13.75,9.916666666666666], [21.875,0.75,8.916666666666666], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // Nightstand drawer 2 bottom (baltic_birch_plywood)
    part([105.875,-12.75,10.916666666666666], [20.625,11.5,0.5], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [], 0, false, false);
    // Nightstand drawer 2 side 1 (baltic_birch_plywood)
    part([105.625,-13.0,10.416666666666666], [0.5,12.0,7.916666666666666], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [0,2,true,0.25,0.5,0.5], 0, false, false);
    // Nightstand drawer 2 side 2 (baltic_birch_plywood)
    part([126.25,-13.0,10.416666666666666], [0.5,12.0,7.916666666666666], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [0,2,false,0.25,0.5,0.5], 0, false, false);
    // Nightstand drawer 2 end 1 (baltic_birch_plywood)
    part([106.125,-13.0,10.416666666666666], [20.125,0.5,7.916666666666666], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [1,2,true,0.25,0.5,0.5], 0, false, false);
    // Nightstand drawer 2 end 2 (baltic_birch_plywood)
    part([106.125,-1.5,10.416666666666666], [20.125,0.5,7.916666666666666], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [1,2,false,0.25,0.5,0.5], 0, false, false);
    // Nightstand drawer front 3 (walnut_solid)
    part([105.25,-13.75,18.958333333333332], [21.875,0.75,8.916666666666666], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // Nightstand drawer 3 bottom (baltic_birch_plywood)
    part([105.875,-12.75,19.958333333333332], [20.625,11.5,0.5], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [], 0, false, false);
    // Nightstand drawer 3 side 1 (baltic_birch_plywood)
    part([105.625,-13.0,19.458333333333332], [0.5,12.0,7.916666666666666], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [0,2,true,0.25,0.5,0.5], 0, false, false);
    // Nightstand drawer 3 side 2 (baltic_birch_plywood)
    part([126.25,-13.0,19.458333333333332], [0.5,12.0,7.916666666666666], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [0,2,false,0.25,0.5,0.5], 0, false, false);
    // Nightstand drawer 3 end 1 (baltic_birch_plywood)
    part([106.125,-13.0,19.458333333333332], [20.125,0.5,7.916666666666666], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [1,2,true,0.25,0.5,0.5], 0, false, false);
    // Nightstand drawer 3 end 2 (baltic_birch_plywood)
    part([106.125,-1.5,19.458333333333332], [20.125,0.5,7.916666666666666], [0.8784313725490196,0.8117647058823529,0.6627450980392157], [], [1,2,false,0.25,0.5,0.5], 0, false, false);
    // N1 Nightstand drawers bottom purpleheart frame (purpleheart_solid)
    part([105.125,-13.75,0], [22.125,0.75,0.75], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], 0, false, false);
    // N1 Nightstand drawers top purpleheart frame (purpleheart_solid)
    part([105.125,-13.75,28.0], [22.125,0.75,0.75], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], 0, false, false);
}

// N2 Nightstand open shelves
module assembly_N2() {
    // N2 Nightstand open shelves left side (walnut_plywood)
    part([104.375,-13.0,28.75], [0.75,13.0,66.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,true,0.25,12.0,0.25], 0, false, false);
    // N2 Nightstand open shelves right side (walnut_plywood)
    part([127.25,-13.0,28.75], [0.75,13.0,66.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,false,0.25,12.0,0.25], 0, false, false);
    // N2 Nightstand open shelves top (walnut_plywood)
    part([105.125,-13.0,94.75], [22.125,13.0,0.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [2,1,false,0.25,12.0,0.25], 0, false, false);
    // N2 Nightstand open shelves shelf 1 (walnut_plywood)
    part([105.125,-13.0,45], [22.125,12.0,0.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // N2 Nightstand open shelves shelf 2 (walnut_plywood)
    part([105.125,-13.0,61.5], [22.125,12.0,0.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // N2 Nightstand open shelves shelf 3 (walnut_plywood)
    part([105.125,-13.0,78], [22.125,12.0,0.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // N2 Nightstand open shelves back (walnut_plywood)
    part([104.875,-1.0,28.75], [22.625,0.25,66.25], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // N2 Nightstand open shelves top mounting brace (walnut_plywood)
    part([105.125,-0.75,91.75], [22.125,0.75,3.0], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // N2 Nightstand open shelves shelf 1 purpleheart frame (purpleheart_solid)
    part([105.125,-13.75,45], [22.125,0.75,0.75], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], 0, false, false);
    // N2 Nightstand open shelves shelf 2 purpleheart frame (purpleheart_solid)
    part([105.125,-13.75,61.5], [22.125,0.75,0.75], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], 0, false, false);
    // N2 Nightstand open shelves shelf 3 purpleheart frame (purpleheart_solid)
    part([105.125,-13.75,78], [22.125,0.75,0.75], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], 0, false, false);
    // N2 Nightstand open shelves top purpleheart frame (purpleheart_solid)
    part([105.125,-13.75,94.75], [22.125,0.75,0.75], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], 0, false, false);
}

// B1 Bridge cabinet
module assembly_B1() {
    // B1 Bridge cabinet left side (walnut_plywood)
    part([45.625,-13.0,72], [0.75,13.0,23.5], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,true,0.25,12.0,0.25], 0, false, false);
    // B1 Bridge cabinet right side (walnut_plywood)
    part([64.45833333333333,-13.0,72], [0.75,13.0,23.5], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,false,0.25,12.0,0.25], 0, false, false);
    // B1 Bridge cabinet top (walnut_plywood)
    part([46.375,-13.0,94.75], [18.083333333333332,13.0,0.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [2,1,false,0.25,12.0,0.25], 0, false, false);
    // B1 Bridge cabinet bottom (walnut_plywood)
    part([46.375,-13.0,72], [18.083333333333332,13.0,0.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [2,1,true,0.25,12.0,0.25], 0, false, false);
    // B1 Bridge cabinet back (walnut_plywood)
    part([46.125,-1.0,72.5], [18.583333333333332,0.25,22.5], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // B1 Bridge cabinet top mounting brace (walnut_plywood)
    part([46.375,-0.75,91.75], [18.083333333333332,0.75,3.0], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // Bridge door 1 (walnut_solid)
    part([46.5,-13.75,72.875], [17.833333333333332,0.75,21.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
}

// B2 Bridge cabinet
module assembly_B2() {
    // B2 Bridge cabinet left side (walnut_plywood)
    part([65.20833333333333,-13.0,72], [0.75,13.0,23.5], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,true,0.25,12.0,0.25], 0, false, false);
    // B2 Bridge cabinet right side (walnut_plywood)
    part([84.04166666666666,-13.0,72], [0.75,13.0,23.5], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,false,0.25,12.0,0.25], 0, false, false);
    // B2 Bridge cabinet top (walnut_plywood)
    part([65.95833333333333,-13.0,94.75], [18.083333333333332,13.0,0.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [2,1,false,0.25,12.0,0.25], 0, false, false);
    // B2 Bridge cabinet bottom (walnut_plywood)
    part([65.95833333333333,-13.0,72], [18.083333333333332,13.0,0.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [2,1,true,0.25,12.0,0.25], 0, false, false);
    // B2 Bridge cabinet back (walnut_plywood)
    part([65.70833333333333,-1.0,72.5], [18.583333333333332,0.25,22.5], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // B2 Bridge cabinet top mounting brace (walnut_plywood)
    part([65.95833333333333,-0.75,91.75], [18.083333333333332,0.75,3.0], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // Bridge door 2 (walnut_solid)
    part([66.08333333333333,-13.75,72.875], [17.833333333333332,0.75,21.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
}

// B3 Bridge cabinet
module assembly_B3() {
    // B3 Bridge cabinet left side (walnut_plywood)
    part([84.79166666666666,-13.0,72], [0.75,13.0,23.5], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,true,0.25,12.0,0.25], 0, false, false);
    // B3 Bridge cabinet right side (walnut_plywood)
    part([103.62499999999999,-13.0,72], [0.75,13.0,23.5], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,false,0.25,12.0,0.25], 0, false, false);
    // B3 Bridge cabinet top (walnut_plywood)
    part([85.54166666666666,-13.0,94.75], [18.083333333333332,13.0,0.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [2,1,false,0.25,12.0,0.25], 0, false, false);
    // B3 Bridge cabinet bottom (walnut_plywood)
    part([85.54166666666666,-13.0,72], [18.083333333333332,13.0,0.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [2,1,true,0.25,12.0,0.25], 0, false, false);
    // B3 Bridge cabinet back (walnut_plywood)
    part([85.29166666666666,-1.0,72.5], [18.583333333333332,0.25,22.5], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // B3 Bridge cabinet top mounting brace (walnut_plywood)
    part([85.54166666666666,-0.75,91.75], [18.083333333333332,0.75,3.0], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // Bridge door 3 (walnut_solid)
    part([85.66666666666666,-13.75,72.875], [17.833333333333332,0.75,21.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
}

// H1 Open headboard carcass
module assembly_H1() {
    // H1 Open headboard carcass back (walnut_plywood)
    part([46.125,-1.0,0.5], [57.75,0.25,71.0], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // H1 Open headboard carcass top mounting brace (walnut_plywood)
    part([46.375,-0.75,68.25], [57.25,0.75,3], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // H1 Open headboard carcass top cap (walnut_plywood)
    part([45.625,-13,71.25], [58.75,13,0.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [2,1,false,0.25,12.0,0.25], 0, false, false);
    // H1 Open headboard carcass bottom (walnut_plywood)
    part([46.375,-13,0], [57.25,13,0.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [2,1,true,0.25,12.0,0.25], 0, false, false);
    // Headboard walnut bed attachment cross brace (walnut_solid)
    part([46.375,-2.5,8], [57.25,0.75,8], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // H1 Open headboard carcass side 1 (walnut_plywood)
    part([45.625,-13,0], [0.75,13,71.25], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,true,0.25,12.0,0.25], 0, false, false);
    // H1 Open headboard carcass side 2 (walnut_plywood)
    part([103.625,-13,0], [0.75,13,71.25], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [0,1,false,0.25,12.0,0.25], 0, false, false);
    // H1 Open headboard carcass purpleheart bottom frame (purpleheart_solid)
    part([46.375,-13.75,0], [57.25,0.75,0.75], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], 0, false, false);
}

// I1 Site-installed top, trim and lighting
module assembly_I1() {
    // Desk top (walnut_solid)
    part([0.75,-24,29.25], [44.125,23.0,1.5], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // Desk LED (led)
    part([2.5,-2.15,47.75], [42,0.4,0.25], [1.0,0.6196078431372549,0.1803921568627451], [], [], 0, false, true);
    // Nightstand LED (led)
    part([105.875,-2.15,44.75], [20.625,0.4,0.25], [1.0,0.6196078431372549,0.1803921568627451], [], [], 0, false, true);
}

// D5 Desk right support panel
module assembly_D5() {
    // Desk right walnut plywood support (walnut_plywood)
    part([44.125,-23.25,0], [0.75,22.25,29.25], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // Desk right support purpleheart face frame (purpleheart_solid)
    part([44.125,-24.0,0.0], [0.75,0.75,29.25], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], 0, false, false);
}

// F1 Bed left rail and ledge
module assembly_F1() {
    // Bed left rail (walnut_solid)
    part([46.5,-78.5,8], [1.5,76,8], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // Bed left slat ledge (walnut_solid)
    part([48,-78.5,14.25], [1,74.5,0.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
}

// F2 Bed right rail and ledge
module assembly_F2() {
    // Bed right rail (walnut_solid)
    part([102,-78.5,8], [1.5,76,8], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // Bed right slat ledge (walnut_solid)
    part([101,-78.5,14.25], [1,74.5,0.75], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
}

// F3 Bed foot assembly
module assembly_F3() {
    // Bed footboard (walnut_solid)
    part([46.5,-80,8], [57.0,1.5,8], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // Bed front left leg (walnut_solid)
    part([46.5,-80,0], [3,1.5,8], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [0.5,0.25], [], 0, false, false);
    // Bed front right leg (walnut_solid)
    part([100.5,-80,0], [3,1.5,8], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [0.5,0.25], [], 0, false, false);
}

// I2 Bed parts - assemble in room
module assembly_I2() {
    // Bed head rail (walnut_solid)
    part([48,-4,8], [54,1.5,8], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // Bed center slat ledge (walnut_solid)
    part([74.25,-78.5,14.0], [3.0,74.5,1.5], [0.4196078431372549,0.27450980392156865,0.17647058823529413], [], [], 0, false, false);
    // Full mattress (linen)
    part([48,-78,15.5], [54,75,10], [0.8901960784313725,0.8392156862745098,0.7411764705882353], [], [], 0, true, false);
    // Bed bridge LED (led)
    part([47.5,-2.15,71.0], [55,0.4,0.25], [1.0,0.6196078431372549,0.1803921568627451], [], [], 0, false, true);
    // Maple solid bed slat (maple_solid)
    part([48,-78.5,15.0], [54,3.5,0.5], [0.7098039215686275,0.592156862745098,0.4470588235294118], [], [], 0, false, false);
    // Maple solid bed slat (maple_solid)
    part([48,-73.03846153846153,15.0], [54,3.5,0.5], [0.7098039215686275,0.592156862745098,0.4470588235294118], [], [], 0, false, false);
    // Maple solid bed slat (maple_solid)
    part([48,-67.57692307692308,15.0], [54,3.5,0.5], [0.7098039215686275,0.592156862745098,0.4470588235294118], [], [], 0, false, false);
    // Maple solid bed slat (maple_solid)
    part([48,-62.11538461538461,15.0], [54,3.5,0.5], [0.7098039215686275,0.592156862745098,0.4470588235294118], [], [], 0, false, false);
    // Maple solid bed slat (maple_solid)
    part([48,-56.65384615384615,15.0], [54,3.5,0.5], [0.7098039215686275,0.592156862745098,0.4470588235294118], [], [], 0, false, false);
    // Maple solid bed slat (maple_solid)
    part([48,-51.19230769230769,15.0], [54,3.5,0.5], [0.7098039215686275,0.592156862745098,0.4470588235294118], [], [], 0, false, false);
    // Maple solid bed slat (maple_solid)
    part([48,-45.730769230769226,15.0], [54,3.5,0.5], [0.7098039215686275,0.592156862745098,0.4470588235294118], [], [], 0, false, false);
    // Maple solid bed slat (maple_solid)
    part([48,-40.26923076923077,15.0], [54,3.5,0.5], [0.7098039215686275,0.592156862745098,0.4470588235294118], [], [], 0, false, false);
    // Maple solid bed slat (maple_solid)
    part([48,-34.80769230769231,15.0], [54,3.5,0.5], [0.7098039215686275,0.592156862745098,0.4470588235294118], [], [], 0, false, false);
    // Maple solid bed slat (maple_solid)
    part([48,-29.346153846153847,15.0], [54,3.5,0.5], [0.7098039215686275,0.592156862745098,0.4470588235294118], [], [], 0, false, false);
    // Maple solid bed slat (maple_solid)
    part([48,-23.884615384615387,15.0], [54,3.5,0.5], [0.7098039215686275,0.592156862745098,0.4470588235294118], [], [], 0, false, false);
    // Maple solid bed slat (maple_solid)
    part([48,-18.42307692307692,15.0], [54,3.5,0.5], [0.7098039215686275,0.592156862745098,0.4470588235294118], [], [], 0, false, false);
    // Maple solid bed slat (maple_solid)
    part([48,-12.961538461538453,15.0], [54,3.5,0.5], [0.7098039215686275,0.592156862745098,0.4470588235294118], [], [], 0, false, false);
    // Maple solid bed slat (maple_solid)
    part([48,-7.5,15.0], [54,3.5,0.5], [0.7098039215686275,0.592156862745098,0.4470588235294118], [], [], 0, false, false);
}

// I3 Shared face frames - fit after installation
module assembly_I3() {
    // Shared purpleheart stile 1 (purpleheart_solid)
    part([44.875,-13.75,0.0], [1.5,0.75,95.5], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], 0, false, false);
    // Shared purpleheart stile 2 (purpleheart_solid)
    part([103.625,-13.75,0.0], [1.5,0.75,95.5], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], 0, false, false);
    // Bed bridge purpleheart stile 1 (purpleheart_solid)
    part([64.45833333333333,-13.75,72.75], [1.5,0.75,22.0], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], 0, false, false);
    // Bed bridge purpleheart stile 2 (purpleheart_solid)
    part([84.04166666666666,-13.75,72.75], [1.5,0.75,22.0], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], 0, false, false);
    // Far left continuous purpleheart stile (purpleheart_solid)
    part([0,-13.75,0], [0.75,0.75,95.5], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], 0, false, false);
    // Far right continuous purpleheart stile (purpleheart_solid)
    part([127.25,-13.75,0], [0.75,0.75,95.5], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], 0, false, false);
}

// I4 Shared horizontal face frames - fit after installation
module assembly_I4() {
    // Desk continuous horizontal purpleheart face frame (purpleheart_solid)
    part([0.75,-13.75,48.0], [44.125,0.75,0.75], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], 0, false, false);
    // Desk top continuous horizontal purpleheart face frame (purpleheart_solid)
    part([0.75,-13.75,94.75], [44.125,0.75,0.75], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], 0, false, false);
    // Bed continuous horizontal purpleheart face frame (purpleheart_solid)
    part([46.375,-13.75,71.25], [57.25,0.75,1.5], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], 0, false, false);
    // Bed top continuous horizontal purpleheart face frame (purpleheart_solid)
    part([46.375,-13.75,94.75], [57.25,0.75,0.75], [0.4117647058823529,0.19607843137254902,0.35294117647058826], [], [], 0, false, false);
}

scale([unit_scale, unit_scale, unit_scale]) {
    if (assembly == "All" || assembly == "D1") assembly_D1();
    if (assembly == "All" || assembly == "D2") assembly_D2();
    if (assembly == "All" || assembly == "D3") assembly_D3();
    if (assembly == "All" || assembly == "N1") assembly_N1();
    if (assembly == "All" || assembly == "N2") assembly_N2();
    if (assembly == "All" || assembly == "B1") assembly_B1();
    if (assembly == "All" || assembly == "B2") assembly_B2();
    if (assembly == "All" || assembly == "B3") assembly_B3();
    if (assembly == "All" || assembly == "H1") assembly_H1();
    if (assembly == "All" || assembly == "I1") assembly_I1();
    if (assembly == "All" || assembly == "D5") assembly_D5();
    if (assembly == "All" || assembly == "F1") assembly_F1();
    if (assembly == "All" || assembly == "F2") assembly_F2();
    if (assembly == "All" || assembly == "F3") assembly_F3();
    if (assembly == "All" || assembly == "I2") assembly_I2();
    if (assembly == "All" || assembly == "I3") assembly_I3();
    if (assembly == "All" || assembly == "I4") assembly_I4();
}
