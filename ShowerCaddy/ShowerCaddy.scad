/*
ShowerCaddy — self-contained OpenSCAD translation of ShowerCaddy.py v3.
All dimensions in mm. Plain front; artwork deliberately removed.
Three printable objects: basket, left arm, right arm. No external libraries.

Select part in Customizer. F5 previews; F6 renders before mesh export.
Export each part separately: SCAD/STL do not preserve Fusion components.
print_layout orients both arms on their straight outer side faces.
Rounded edges use CSG sweeps, not Fusion's BRep fillet solver; small blended
junctions can differ while nominal dimensions and mating sections are retained.
Console diagnostics can be captured beside this file with CLI redirection:
  openscad -o /tmp/caddy.3mf ShowerCaddy.scad 2> ShowerCaddy.scad.log
OpenSCAD itself cannot write a sidecar log from the modeling language.
*/

/* [View and output] */
part = "assembly"; // [assembly,basket,left_arm,right_arm,print_layout,exploded]
/* [Basket dimensions in mm] */
basket_width = 259;
basket_depth = 88.9;
side_height = 101.6;
wall_thickness = 3;
floor_thickness = 3;
/* [Hooks in mm] */
hook_rise = 305;
rise_from_rim = false;
hook_clearance = 25.5;
hook_width = 25;
hook_thickness = 10;
hook_return_drop = 30;
/* [Drainage in mm] */
mesh_opening = 8;
mesh_web = 3;
mesh_border = 6;
/* [Reinforcement and sliding joints in mm] */
arm_bottom = 15;
root_web_width = 20;
root_taper_height = 40;
socket_depth = 12;
shoulder_height = 4;
tongue_neck = 25;
tongue_head = 33;
tongue_step = 3.3;
tongue_depth = 8;
tongue_top_margin = 10;
joint_clearance = 0.30; // Per mating side
shoulder_width = 39;
shoulder_depth = 10;
/* [Rounding in mm] */
edge_radius = 0.75;
corner_radius = 1;
hook_bend_radius = 4;
joint_radius = 0.4;
joint_edge_radius = 0.2;
/* [Resolution] */
curve_segments = 48;
arc_steps = 16;
/* [Hidden] */
$fn = curve_segments;
eps = 0.02;
bridge_z = hook_rise + (rise_from_rim ? side_height : 0);
root_width = hook_width + root_web_width;
seat_z = arm_bottom + shoulder_height;
tongue_top = side_height - tongue_top_margin;
pitch = mesh_opening + mesh_web;
nx = floor((basket_width-2*mesh_border+mesh_web)/pitch);
ny = floor((basket_depth-2*mesh_border+mesh_web)/pitch);
mesh_x = (basket_width-(nx*pitch-mesh_web))/2;
mesh_y = (basket_depth-(ny*pitch-mesh_web))/2;
black_pla = [0.0784,0.0784,0.0784];

assert(basket_width>2*root_width && basket_depth>2*wall_thickness);
assert(floor_thickness>2*edge_radius && wall_thickness>2*edge_radius);
assert(mesh_web>2*edge_radius && nx>0 && ny>0);
assert(root_web_width>0 && root_web_width<root_taper_height);
assert(side_height+root_taper_height<bridge_z-hook_return_drop);
assert(hook_clearance>2*hook_bend_radius);
assert(tongue_head+2*joint_clearance+2*wall_thickness<root_width);
assert(tongue_neck+2*joint_clearance<tongue_head);
assert(socket_depth-tongue_depth-joint_clearance>=wall_thickness);
assert(seat_z<tongue_top && tongue_top<side_height);
assert(shoulder_width>tongue_head+2*joint_clearance+2*joint_radius);
assert(shoulder_depth>tongue_depth+joint_clearance+2*joint_radius);
assert(shoulder_width<root_width && shoulder_depth<socket_depth);
assert(curve_segments>=16 && arc_steps>=4);
assert(len([for(p=["assembly","basket","left_arm","right_arm","print_layout","exploded"]) if(p==part) p])>0,
       "Unknown part selection");
echo(revision="sliding-tongue-groove-v3-scad",part=part);
echo(basket_mm=[basket_width,basket_depth,side_height],front_wall_mm=wall_thickness);
echo(hook_rise_mm=bridge_z,glass_throat_mm=hook_clearance,overall_height_mm=bridge_z+hook_thickness);
echo(arm_mm=[hook_width,hook_thickness],root_width_mm=root_width,drainage_grid=[nx,ny]);
echo(joint_clearance_per_side_mm=joint_clearance,engagement_mm=tongue_top-seat_z);

function unit2(v) = v/norm(v);
function cross2(a,b) = a[0]*b[1]-a[1]*b[0];
function corner_points(p,i,r,n) =
    let(v=p[i],u=unit2(p[(i+len(p)-1)%len(p)]-v),w=unit2(p[(i+1)%len(p)]-v),
        angle=acos(max(-1,min(1,u*w))),t=r/tan(angle/2),
        a=v+u*t,b=v+w*t,c=v+unit2(u+w)*(r/sin(angle/2)),
        aa=atan2(a[1]-c[1],a[0]-c[0]),ab=atan2(b[1]-c[1],b[0]-c[0]),
        direction=cross2(v-p[(i+len(p)-1)%len(p)],p[(i+1)%len(p)]-v)>0?1:-1,
        sweep=direction>0?((ab-aa+360)%360):-((aa-ab+360)%360))
    [for(k=[0:n]) k==0?a:k==n?b:c+r*[cos(aa+sweep*k/n),sin(aa+sweep*k/n)]];
function rounded_polygon(p,r,n=8) = [for(i=[0:len(p)-1]) each corner_points(p,i,r,n)];
function joint_section(c=0) =
    let(n=tongue_neck/2+c,h=tongue_head/2+c,s=tongue_step-c,d=tongue_depth+c)
    [[-n,-1],[n,-1],[n,s],[h,s],[h,d],[-h,d],[-h,s],[-n,s]];
function taper_points() =
    let(w=root_web_width,h=root_taper_height,r=(w*w+h*h)/(4*w),theta=2*atan(w/h))
    concat([for(i=[0:arc_steps]) let(a=theta*i/arc_steps)
        [root_width-r+r*cos(a),side_height+r*sin(a)]],
        [for(i=[1:arc_steps]) let(a=theta*(1-i/arc_steps))
        [hook_width+r-r*cos(a),side_height+h-r*sin(a)]]);

module rounded_rect(w,d,r) {
    translate([r,r]) offset(r=r) square([w-2*r,d-2*r]);
}
// Rounds convex AND concave corners of an otherwise sharp planar outline.
module soften_2d(r) {
    offset(r=r) offset(delta=-r) offset(r=-r) offset(delta=r) children();
}
// Preserve section extents and total height while rounding extrusion ends.
module eased_extrude(h,r) {
    assert(h>2*r);
    translate([0,0,r]) minkowski() {
        linear_extrude(height=h-2*r,convexity=12) offset(delta=-r) children();
        resize([2*r,2*r,2*r]) sphere(r=r,$fn=24);
    }
}
module rounded_box(size,r=edge_radius) {
    eased_extrude(size[2],r) rounded_rect(size[0],size[1],corner_radius);
}
module joint_prism(z0,z1,clearance=0,ease=false) {
    translate([0,0,z0])
        if(ease) eased_extrude(z1-z0,joint_edge_radius)
            polygon(rounded_polygon(joint_section(clearance),joint_radius));
        else linear_extrude(height=z1-z0,convexity=6)
            polygon(rounded_polygon(joint_section(clearance),joint_radius));
}
module shoulder_section(clearance=0) {
    half=shoulder_width/2+clearance;
    polygon(rounded_polygon([[-half,-1],[half,-1],[half,shoulder_depth+clearance],
                             [-half,shoulder_depth+clearance]],joint_radius));
}

// Rounded square holes with a quarter-circle relief at both floor surfaces.
// A ring loft avoids expensive 3D Minkowski operations on the entire mesh.
function rect_ring(w,r,n=8) = [for(k=[0:3]) each
    let(c=k==0?[w-r,r]:k==1?[w-r,w-r]:k==2?[r,w-r]:[r,r])
    [for(i=[0:n]) c+r*[cos(-90+k*90+i*90/n),sin(-90+k*90+i*90/n)]]];
module drain_hole() {
    n=8; count=4*(n+1); r=edge_radius;
    zs=concat([-eps], [for(i=[0:8]) r*(1-cos(i*90/8))],
              [for(i=[0:8]) floor_thickness-r+r*sin(i*90/8)], [floor_thickness+eps]);
    function relief(z) = z<0 || z>floor_thickness ? r :
        z<r ? r-sqrt(max(0,r*r-(r-z)*(r-z))) :
        z>floor_thickness-r ? r-sqrt(max(0,r*r-(z-floor_thickness+r)*(z-floor_thickness+r))) : 0;
    points=[for(z=zs) each let(d=relief(z))
        [for(p=rect_ring(mesh_opening+2*d,corner_radius+d,n)) [p[0]-d,p[1]-d,z]]];
    faces=concat([[for(i=[count-1:-1:0]) i]],
        [for(j=[0:len(zs)-2],i=[0:count-1])
            [j*count+i,j*count+(i+1)%count,(j+1)*count+(i+1)%count,(j+1)*count+i]],
        [[for(i=[0:count-1]) (len(zs)-1)*count+i]]);
    // OpenSCAD polyhedron faces use clockwise winding viewed from outside.
    polyhedron(points=points,faces=[for(f=faces) [for(i=[len(f)-1:-1:0]) f[i]]],convexity=6);
}
module basket() {
    color(black_pla) difference() {
        union() {
            rounded_box([basket_width,basket_depth,floor_thickness]);
            eased_extrude(side_height,edge_radius) difference() {
                rounded_rect(basket_width,basket_depth,corner_radius);
                translate([wall_thickness,wall_thickness])
                    rounded_rect(basket_width-2*wall_thickness,basket_depth-2*wall_thickness,corner_radius);
            }
            for(x=[0,basket_width-root_width])
                translate([x,0,seat_z]) rounded_box([root_width,socket_depth,side_height-seat_z]);
        }
        for(ix=[0:nx-1],iy=[0:ny-1])
            translate([mesh_x+ix*pitch,mesh_y+iy*pitch,0]) drain_hole();
        for(center=[root_width/2,basket_width-root_width/2]) translate([center,0,0]) {
            // Open through floor/back below socket: shoulder insertion path.
            translate([0,0,-1]) linear_extrude(height=seat_z+1)
                shoulder_section(joint_clearance);
            joint_prism(seat_z-1,side_height+1,joint_clearance);
        }
    }
}
module arm_stem() {
    // Local XY is model XZ; extrusion goes toward negative Y.
    rotate([90,0,0]) eased_extrude(hook_thickness,edge_radius)
        soften_2d(corner_radius) polygon(concat(
            [[0,arm_bottom],[root_width,arm_bottom]],taper_points(),
            [[hook_width,bridge_z+hook_thickness],[0,bridge_z+hook_thickness]]));
}
module hook_cap() {
    rear=-hook_thickness; far=rear-hook_clearance;
    r=hook_bend_radius; bottom=bridge_z-hook_return_drop;
    // YZ outline, including both R4 inside corners. Bottom overlap joins stem.
    p=concat([[0,bottom],[0,bridge_z+hook_thickness],
              [far-hook_thickness,bridge_z+hook_thickness],[far-hook_thickness,bottom],
              [far,bottom],[far,bridge_z-r]],
             [for(i=[1:arc_steps]) let(a=180-90*i/arc_steps)
                [far+r+r*cos(a),bridge_z-r+r*sin(a)]],
             [[rear-r,bridge_z]],
             [for(i=[1:arc_steps]) let(a=90-90*i/arc_steps)
                [rear-r+r*cos(a),bridge_z-r+r*sin(a)]],[[rear,bottom]]);
    multmatrix([[0,0,1,0],[1,0,0,0],[0,1,0,0],[0,0,0,1]])
        eased_extrude(hook_width,edge_radius) soften_2d(corner_radius) polygon(p);
}
module left_arm() {
    color(black_pla) union() {
        arm_stem();
        hook_cap();
        translate([root_width/2,0,arm_bottom])
            eased_extrude(shoulder_height,joint_edge_radius) shoulder_section();
        translate([root_width/2,0,0]) joint_prism(seat_z-0.5,tongue_top,0,true);
    }
}
module right_arm() { translate([basket_width,0,0]) mirror([1,0,0]) left_arm(); }
module assembled(explode=0) {
    translate([0,explode,0]) basket();
    translate([-explode,0,0]) left_arm();
    translate([explode,0,0]) right_arm();
}
module arm_on_bed() {
    // Model X -> print Z, model Z -> print X. Outer X=0 face touches bed.
    multmatrix([[0,0,1,-arm_bottom],[0,-1,0,shoulder_depth],[1,0,0,0],[0,0,0,1]]) left_arm();
}
module print_layout() {
    basket();
    translate([0,basket_depth+15,0]) arm_on_bed();
    translate([0,basket_depth+85,0]) mirror([0,1,0])
        translate([0,-(shoulder_depth+2*hook_thickness+hook_clearance),0]) arm_on_bed();
}
if(part=="basket") basket();
else if(part=="left_arm") left_arm();
else if(part=="right_arm") right_arm();
else if(part=="print_layout") print_layout();
else if(part=="exploded") assembled(35);
else assembled();
