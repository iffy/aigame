

var world, mass, tickables=[], moveables=[], timeStep=1/60,
         ground, camera, scene, renderer, materials, playing = true,
    inputs = {};

// start
initThree();
initPhysics();
initKeyboard();
animate();
scene1();

function initPhysics() {
    // define the world
    world = new CANNON.World();
    world.gravity.set(0, 0, -24.82);
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
            friction: 0, restitution: 0.2,
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
    camera.position.z = 15;
    camera.position.y = -5;
    camera.rotation.x = 0.2;
    scene.add( camera );

    // ambient light
    var light = new THREE.AmbientLight(0x404040);
    scene.add(light);

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

    // critter
    var critter = new BoxCritter();
    critter.controlled_by_inputs = true;
    world.addBody(critter.body);
    scene.add(critter.mesh);
    moveables.push(critter);
}

//-------------------------------------------------------------------
// Keyboard input
var KEYS = {
    'w': 87,
    'd': 68,
    'a': 65,
    's': 83,
    'escape': 27,
    'space': 32,
}
var KEYSinv = _.invert(KEYS);
function initKeyboard() {
    window.addEventListener('keydown', function(e) {
        if (e.keyCode == KEYS.escape) {
            // ESC == pause
            playing = !playing;
            console.log('playing', playing);
            return false;
        } else if (KEYSinv[e.keyCode]) {
            inputs[KEYSinv[e.keyCode]] = true;
            return false;
        } else {
            console.log(e.keyCode);
        }
    });
    window.addEventListener('keyup', function(e) {
        if (KEYSinv[e.keyCode]) {
            delete inputs[KEYSinv[e.keyCode]];
            return false;
        }
    });
}



//-------------------------------------------------------------------
// A Box Critter
//
function BoxCritter(options) {
    var options = options || {};
    var size = options.size || 2;
    var color = options.color || 0x99eeff;

    this.mesh = null;
    this.body = null;
    this.alive = true;
    this.max_move_speed = 6;
    this.acceleration = 1.2;
    this.controlled_by_inputs = false;
    this.target_facing = 0;

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
      position: new CANNON.Vec3(0, 0, 1),
      angularDamping: 0.1,
      linearFactor: new CANNON.Vec3(0.99, 0.99, 0),
      //linearDamping: 0.999999,
    });

    this.body.material = materials.boxcritter;
    this.body.addShape(shape);
    tickables.push(this);
    return this;
}

BoxCritter.prototype.tick = function(e) {
    if (!this.alive) {
        return;
    }
    if (this.controlled_by_inputs) {
        // axis movement
        var y = this.body.velocity.y * 0.5;
        var x = this.body.velocity.x * 0.5;
        var z = this.body.velocity.z;
        if (inputs.w) {
            y += this.max_move_speed;
            this.target_facing = 0.5 * Math.PI;
        }
        if (inputs.s) {
            y -= this.max_move_speed;
            this.target_facing = 1.5 * Math.PI;
        }
        if (inputs.a) {
            x -= this.max_move_speed;
            this.target_facing = Math.PI;
        }
        if (inputs.d) {
            x += this.max_move_speed;
            this.target_facing = 0;
        }
        if (inputs.space) {
            z = 5;
        }
        this.body.velocity.set(x, y, z);

        // facing
        this.body.quaternion.setFromAxisAngle(new CANNON.Vec3(0, 0, 1),
                this.target_facing);
    }
}
BoxCritter.prototype.updateView = function() {
    this.mesh.position.copy(this.body.position);
    this.mesh.quaternion.copy(this.body.quaternion);
}

