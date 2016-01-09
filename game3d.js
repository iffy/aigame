

var world, mass, tickables=[], moveables=[], timeStep=1/60,
         ground, camera, scene, renderer, materials, playing = true;

// start
initThree();
initPhysics();
initKeyboard();
animate();
scene1();

function initPhysics() {
    // define the world
    world = new CANNON.World();
    world.gravity.set(0, 0, -9.82);
    world.broadphase = new CANNON.NaiveBroadphase();
    world.solver.iterations = 10;

    // add materials
    materials = {
        'concrete': new CANNON.Material(),
        'boxcritter': new CANNON.Material(),
    };

    // material interactions
    world.addContactMaterial(new CANNON.ContactMaterial(
        materials.concrete, materials.boxcritter, {
            friction: 0.1, restitution: 0.2,
        }));

    // add a plane
    ground = new CANNON.Body({
      mass: 0 // mass == 0 makes the body static
    });
    ground.material = materials.concrete;
    var groundShape = new CANNON.Plane();
    ground.addShape(groundShape);
    world.addBody(ground);
}
function initThree() {
    scene = new THREE.Scene();

    // camera
    camera = new THREE.PerspectiveCamera( 75, window.innerWidth / window.innerHeight, 1, 100 );
    camera.position.z = 25;
    scene.add( camera );

    // ambient light
    var light = new THREE.AmbientLight(0x404040);
    scene.add(light);

    // other lights
    var light = new THREE.SpotLight(0xffffff);
    light.position.set(100, 100, 100);
    scene.add( light );

    // ground plane
    var geometry = new THREE.PlaneGeometry(10, 10);
    var material = new THREE.MeshPhongMaterial({color: 0x005500, shading: THREE.FlatShading, side: THREE.DoubleSide});
    var plane = new THREE.Mesh( geometry, material );
    plane.receiveShadow = true;
    scene.add( plane );

    // renderer
    renderer = new THREE.WebGLRenderer({antialias: true});
    renderer.setSize( window.innerWidth, window.innerHeight );
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    document.body.appendChild( renderer.domElement );
}
var last_time = 0;
function animate(f) {
    requestAnimationFrame(animate);
    var tick = {
        delta: f - last_time,
    }
    last_time = f;
    if (playing) {
        tickables.forEach(function(x) {
            x.tick(tick);
        })
        updatePhysics();
        render();
    }
}
function updatePhysics() {
    // Step the physics world
    world.step(timeStep);
    // Copy coordinates from physics to display
    for (var i = 0; i < moveables.length; i++) {
      moveables[i].updateView();
    }
}
function render() {
    renderer.render( scene, camera );
}


function scene1() {
    var critter = new BoxCritter();
    world.addBody(critter.body);
    scene.add(critter.mesh);
    moveables.push(critter);
}

//-------------------------------------------------------------------
// Keyboard input
function initKeyboard() {
    window.addEventListener('keydown', function(e) {
        console.log(e.keyCode);
        if (e.keyCode == 80) {
            // p == pause
            playing = !playing;
        }
    })
}



//-------------------------------------------------------------------
// A Box Critter
//
function BoxCritter(options) {
    var options = options || {};
    var size = options.size || 2;
    var color = options.color || 0xeeeeff;

    this.mesh = null;
    this.body = null;
    this.alive = true;
    this.cat_mode = true;

    // visual manifestation
    var geometry = new THREE.BoxGeometry(size, size, size);
    var material = new THREE.MeshPhongMaterial({
        color: color,
        shading: THREE.FlatShading,
    });
    this.mesh = new THREE.Mesh(geometry, material);

    // physics
    var shape = new CANNON.Box(new CANNON.Vec3(size/2,size/2,size/2));
    this.body = new CANNON.Body({
      mass: 100,
      position: new CANNON.Vec3(0, 0, 10),
      angularDamping: 0.2,
    });

    console.log(this.body);
    this.body.material = materials.boxcritter;
    this.body.angularVelocity.set(3, 10, 20);
    this.body.addShape(shape);
    tickables.push(this);
    return this;
}

BoxCritter.prototype.tick = function(e) {
    if (!this.alive) {
        return;
    }
    if (this.cat_mode) {
        // land on your feet.
        var quat = this.body.quaternion;
        console.log(this.body);
        var opp = quat.clone();
        console.log('opp', opp);
        console.log(this.body.angularVelocity);
        var current = this.body.angularVelocity;
        this.body.angularVelocity.set(
            current.x+opp.x/3,
            current.y+opp.y/3,
            current.z+opp.z/3);
    }
}
BoxCritter.prototype.updateView = function() {
    this.mesh.position.copy(this.body.position);
    this.mesh.quaternion.copy(this.body.quaternion);
}

