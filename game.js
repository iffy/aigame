

var world, mass, bodies=[], timeStep=1/60,
         camera, scene, renderer;
initThree();
initCannon();
animate();

addBox();
function initCannon() {
    // define the world
    world = new CANNON.World();
    world.gravity.set(0, 0, -9.82);
    world.broadphase = new CANNON.NaiveBroadphase();
    world.solver.iterations = 10;

    // add a plane
    var groundBody = new CANNON.Body({
      mass: 0 // mass == 0 makes the body static
    });
    var groundShape = new CANNON.Plane();
    groundBody.addShape(groundShape);
    world.addBody(groundBody);
}
function initThree() {
    scene = new THREE.Scene();

    // camera
    camera = new THREE.PerspectiveCamera( 75, window.innerWidth / window.innerHeight, 1, 100 );
    camera.position.z = 15;
    scene.add( camera );

    // ambient light
    var light = new THREE.AmbientLight(0x404040);
    scene.add(light);

    // other lights
    //addPointLight(0x404040, [1, 1, 10], 1, 100);
    //addPointLight(0xffffff, [-5, -5, 10], 1, 15);
    var light = new THREE.DirectionalLight(0xffffff, 1);
    light.position.set(0, 1, 1);
    light.castShadow = true;
    light.shadowCameraVisible = true;
    scene.add( light );

    // ground plane
    var geometry = new THREE.PlaneGeometry(10, 10);
    var material = new THREE.MeshPhongMaterial({color: 0x005500, shading: THREE.FlatShading, side: THREE.DoubleSide});
    var plane = new THREE.Mesh( geometry, material );
    plane.receiveShadow = true;
    scene.add( plane );

    // renderer
    renderer = new THREE.WebGLRenderer({antialias: true});
    renderer.shadowMap.enabled = true;
    renderer.setSize( window.innerWidth, window.innerHeight );
    document.body.appendChild( renderer.domElement );
}

function addBox() {
    // visual manifestation
    var geometry = new THREE.BoxGeometry( 2, 2, 2 );
    var material = new THREE.MeshPhongMaterial( { color: 0x0088cc, shading: THREE.FlatShading } );
    var mesh = new THREE.Mesh( geometry, material );
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    scene.add( mesh );

    // physics
    var shape = new CANNON.Box(new CANNON.Vec3(2,2,2));
    var body = new CANNON.Body({
      mass: 1,
      position: new CANNON.Vec3(0, 0, 10)
    });
    body.addShape(shape);

    // make it spin
    body.angularVelocity.set(3,10,0);
    body.angularDamping = 0.2;

    world.addBody(body);

    bodies.push([mesh, body]);
}

function addPointLight(color, pos, intensity, distance) {
  intensity = intensity || 1;
  distance = distance || 100;
  var light = new THREE.PointLight(color, intensity, distance);
  light.position.set(pos[0], pos[1], pos[2]);
  scene.add(light);
}

function animate() {
    requestAnimationFrame( animate );
    updatePhysics();
    render();
}
function updatePhysics() {
    // Step the physics world
    world.step(timeStep);
    // Copy coordinates from Cannon.js to Three.js
    for (var i = 0; i < bodies.length; i++) {
      var mesh = bodies[i][0];
      var body = bodies[i][1];
      mesh.position.copy(body.position);
      mesh.quaternion.copy(body.quaternion);
    }
}
function render() {
    renderer.render( scene, camera );
}