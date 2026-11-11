/* Dashboard interactions backed by the PrevenIA API. */
(() => {
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const riskLabels = { low: 'Bajo', medium: 'Medio', high: 'Alto', critical: 'Crítico' };
  const riskClasses = { low: 'risk-low', medium: 'risk-medium', high: 'risk-high', critical: 'risk-critical' };
  const jointLabels = {
    knee_left: 'Rodilla izquierda', knee_right: 'Rodilla derecha',
    hip_left: 'Cadera izquierda', hip_right: 'Cadera derecha',
    shoulder_left: 'Hombro izquierdo', shoulder_right: 'Hombro derecho',
    elbow_left: 'Codo izquierdo', elbow_right: 'Codo derecho',
    ankle_left: 'Tobillo izquierdo', ankle_right: 'Tobillo derecho',
    spine_lateral: 'Columna (lateral)', spine_sagittal: 'Columna (sagital)',
    pelvis_tilt: 'Inclinación pélvica', head_tilt: 'Inclinación de cabeza',
  };
  const normalRanges = {
    knee_left: [165, 180], knee_right: [165, 180],
    hip_left: [170, 190], hip_right: [170, 190],
    shoulder_left: [160, 180], shoulder_right: [160, 180],
    spine_lateral: [0, 5], pelvis_tilt: [0, 10], head_tilt: [0, 5],
  };
  const exerciseGuides = {
    squat: {
      camera: 'Cámara: lateral o 45°',
      tip: 'Coloca los pies al ancho de los hombros y mantén todo el cuerpo visible.',
      steps: ['De pie, pecho abierto y pies firmes.', 'Lleva la cadera atrás y flexiona las rodillas sin que colapsen hacia dentro.', 'Empuja el suelo y vuelve a estar de pie con control.'],
    },
    push_up: {
      camera: 'Cámara: lateral',
      tip: 'Alinea la cámara con tu costado y deja visibles cabeza, tronco y manos.',
      steps: ['Apoya manos bajo los hombros y forma una línea recta con el cuerpo.', 'Flexiona los codos y acerca el pecho al suelo manteniendo el tronco firme.', 'Empuja el suelo hasta extender los brazos sin arquear la espalda.'],
    },
    lunge: {
      camera: 'Cámara: frontal o 45°',
      tip: 'Deja espacio para que se vean ambos pies y rodillas durante el paso.',
      steps: ['Ponte erguido con los pies separados al ancho de caderas.', 'Da un paso y baja controlado; la rodilla delantera sigue la dirección del pie.', 'Empuja con el pie delantero y regresa; alterna las piernas.'],
    },
    arm_raise: {
      camera: 'Cámara: frontal',
      tip: 'Coloca la cámara de frente y asegúrate de que entren manos y hombros en la imagen.',
      steps: ['Ponte erguido con los brazos relajados a los lados.', 'Eleva ambos brazos lateralmente hasta una altura cómoda, sin encoger los hombros.', 'Bájalos despacio y vuelve a la posición inicial.'],
    },
    joint_mobility: {
      camera: 'Cámara: frontal',
      tip: 'Mantén la articulación que quieres evaluar despejada y visible.',
      steps: ['Adopta una postura estable y relajada.', 'Mueve la articulación seleccionada lentamente dentro de un rango cómodo.', 'Regresa al inicio sin rebotes ni movimientos bruscos.'],
    },
    general: {
      camera: 'Cámara: frontal',
      tip: 'Aléjate lo suficiente para que se vea el cuerpo completo, incluidos los pies.',
      steps: ['Párate de forma natural con los pies al ancho de caderas.', 'Mira al frente, relaja los brazos y evita inclinarte o girar.', 'Mantén la posición unos segundos respirando con normalidad.'],
    },
    deadlift: {
      camera: 'Cámara: lateral',
      tip: 'Ubica la cámara de lado para que se aprecien cadera, espalda y rodillas.',
      steps: ['Párate con los pies al ancho de caderas y el peso cerca del cuerpo.', 'Lleva la cadera atrás, flexiona ligeramente las rodillas y mantén la espalda neutra.', 'Empuja el suelo y extiende la cadera para volver a estar de pie.'],
    },
    glute_bridge: {
      camera: 'Cámara: lateral',
      tip: 'Coloca la cámara de lado y asegúrate de que se vea el cuerpo desde hombros hasta rodillas.',
      steps: ['Acuéstate boca arriba con rodillas flexionadas y pies apoyados.', 'Aprieta suavemente los glúteos y eleva la pelvis sin arquear la espalda.', 'Baja la pelvis despacio hasta el suelo.'],
    },
    calf_raise: {
      camera: 'Cámara: lateral o frontal',
      tip: 'Deja los tobillos y pies dentro del encuadre; usa una pared para apoyarte si hace falta.',
      steps: ['Ponte erguido con los pies paralelos y el peso repartido.', 'Eleva los talones lentamente, sin inclinar el cuerpo.', 'Baja con control hasta apoyar los talones.'],
    },
    step_up: {
      camera: 'Cámara: frontal o 45°',
      tip: 'Usa un escalón firme y deja visibles los pies, las rodillas y la superficie.',
      steps: ['Ponte frente a un escalón bajo y estable.', 'Apoya un pie completo y sube empujando con esa pierna, sin dejar que la rodilla se meta hacia dentro.', 'Baja con control y repite con la otra pierna.'],
    },
    jump_landing: {
      camera: 'Cámara: frontal',
      tip: 'Deja espacio alrededor y muestra el cuerpo entero durante el salto y el aterrizaje.',
      steps: ['Párate con los pies al ancho de hombros y las rodillas suaves.', 'Haz un salto pequeño y aterriza sobre ambos pies.', 'Amortigua flexionando cadera y rodillas, mantén el equilibrio y detente.'],
    },
    overhead_press: {
      camera: 'Cámara: frontal',
      tip: 'Deja visibles manos, codos y hombros; usa una carga ligera o solo el movimiento.',
      steps: ['Empieza con las manos a la altura de los hombros y el tronco estable.', 'Empuja las manos hacia arriba sin arquear la zona lumbar.', 'Baja despacio hasta la altura de los hombros.'],
    },
    biceps_curl: {
      camera: 'Cámara: frontal o lateral',
      tip: 'Encuadra desde la cintura hasta las manos para que se vean los codos.',
      steps: ['Ponte erguido con los brazos a los lados y codos cerca del cuerpo.', 'Flexiona los codos y acerca las manos a los hombros sin balancear el tronco.', 'Extiende los brazos lentamente hasta volver al inicio.'],
    },
    row: {
      camera: 'Cámara: lateral',
      tip: 'Coloca la cámara de lado para que se aprecie la inclinación del tronco.',
      steps: ['Inclina la cadera atrás con espalda neutra y brazos extendidos.', 'Lleva los codos hacia atrás cerca del cuerpo, sin encoger los hombros.', 'Extiende los brazos despacio manteniendo estable el tronco.'],
    },
    triceps_dip: {
      camera: 'Cámara: lateral',
      tip: 'Usa una silla o banco firme contra la pared y encuadra brazos y tronco.',
      steps: ['Apoya las manos en el borde estable, con hombros lejos de las orejas.', 'Flexiona los codos para bajar solo hasta un rango cómodo.', 'Empuja con las manos para volver arriba sin bloquear bruscamente los codos.'],
    },
    plank: {
      camera: 'Cámara: lateral',
      tip: 'Coloca la cámara a la altura del tronco para ver la alineación del cuerpo.',
      steps: ['Apoya antebrazos y puntas de los pies; coloca codos bajo los hombros.', 'Activa abdomen y glúteos y mantén cabeza, espalda y cadera alineadas.', 'Respira con normalidad y termina apoyando las rodillas con control.'],
    },
    side_plank: {
      camera: 'Cámara: frontal o 45°',
      tip: 'Gira el cuerpo de lado hacia la cámara y mantén visibles hombro, cadera y pies.',
      steps: ['Apoya un antebrazo bajo el hombro y coloca un pie sobre el otro o escalonados.', 'Eleva la cadera y forma una línea recta de hombros a pies.', 'Baja con control; cambia de lado para repetir.'],
    },
    crunch: {
      camera: 'Cámara: lateral',
      tip: 'Coloca la cámara de lado para mostrar el movimiento del tronco.',
      steps: ['Acuéstate boca arriba con rodillas flexionadas y pies apoyados.', 'Eleva suavemente cabeza y hombros contrayendo el abdomen, sin tirar del cuello.', 'Baja despacio hasta apoyar los hombros.'],
    },
    burpee: {
      camera: 'Cámara: lateral',
      tip: 'Deja espacio para moverte y encuadra el cuerpo completo en todas las fases.',
      steps: ['Empieza de pie y baja flexionando cadera y rodillas para apoyar las manos.', 'Lleva los pies atrás a una plancha; puedes hacerlo paso a paso, sin salto.', 'Acerca los pies de nuevo y ponte de pie con control.'],
    },
    jumping_jack: {
      camera: 'Cámara: frontal',
      tip: 'Aléjate para que entren manos y pies; comprueba que no haya obstáculos.',
      steps: ['Empieza de pie con brazos a los lados y pies juntos.', 'Separa los pies con un salto suave mientras elevas los brazos.', 'Vuelve al centro con control; usa pasos laterales si prefieres evitar el salto.'],
    },
    mountain_climber: {
      camera: 'Cámara: lateral',
      tip: 'Coloca la cámara de lado para ver la línea de hombros, cadera y tobillos.',
      steps: ['Adopta una plancha alta con manos bajo los hombros.', 'Lleva una rodilla hacia el pecho sin elevar demasiado la cadera.', 'Regresa el pie y alterna; empieza despacio y mantén el tronco estable.'],
    },
  };
  const exerciseIllustrationGroups = {
    squat: 'squat',
    push_up: 'pushUp',
    lunge: 'lunge',
    arm_raise: 'armRaise',
    joint_mobility: 'mobility',
    general: 'standing',
    deadlift: 'hinge',
    glute_bridge: 'bridge',
    calf_raise: 'calfRaise',
    step_up: 'stepUp',
    jump_landing: 'landing',
    overhead_press: 'overheadPress',
    biceps_curl: 'curl',
    row: 'row',
    triceps_dip: 'dip',
    plank: 'plank',
    side_plank: 'sidePlank',
    crunch: 'crunch',
    burpee: 'burpee',
    jumping_jack: 'jumpingJack',
    mountain_climber: 'mountainClimber',
  };
  const exerciseReferenceImages = {
    squat: {
      src: 'assets/exercise-guides/squat-reference.png',
      alt: 'Ilustración de una sentadilla: posición baja, extensión de pie y nueva bajada.',
      stages: ['Posición baja', 'Extiende cadera y rodillas', 'Vuelve a bajar con control'],
    },
    push_up: {
      src: 'assets/exercise-guides/push-up-reference.png',
      alt: 'Ilustración de una flexión: posición alta de plancha y bajada controlada hacia el suelo.',
      stages: ['Plancha alta: manos bajo hombros y cuerpo alineado', 'Baja el pecho flexionando los codos', 'Empuja el suelo y vuelve arriba'],
    },
    lunge: {
      src: 'assets/exercise-guides/lunge-reference.png',
      alt: 'Ilustración de una zancada: posición de pie con paso amplio y descenso controlado hasta flexionar ambas rodillas.',
      stages: ['Da un paso amplio y mantén el tronco erguido', 'Baja controlado; la rodilla sigue la dirección del pie', 'Empuja el suelo y vuelve a la posición inicial'],
    },
    arm_raise: {
      src: 'assets/exercise-guides/arm-raise-reference.png',
      alt: 'Ilustración de elevación frontal de brazos: desde los brazos relajados hasta la altura de los hombros.',
      stages: ['Ponte erguido con los brazos relajados', 'Eleva los brazos al frente hasta los hombros', 'Bájalos despacio, sin encoger los hombros'],
    },
    joint_mobility: {
      src: 'assets/exercise-guides/joint-mobility-reference.png',
      alt: 'Lámina de movilidad para espalda y cadera: rotaciones de tronco sentado, inclinaciones laterales, rotaciones de cadera y balanceos de pierna con apoyo.',
      stages: ['Rota el tronco sentado y haz inclinaciones laterales', 'Gira las caderas con suavidad', 'Balancea una pierna con apoyo; repite al otro lado'],
    },
    general: {
      src: 'assets/exercise-guides/standing-posture-reference.png',
      alt: 'Comparación de postura de pie: balanceo posterior, lordosis lumbar, cifosis torácica, cabeza adelantada y alineación correcta.',
      stages: ['Observa de lado la cabeza, los hombros y la cadera', 'Revisa que el tronco no se incline hacia delante o atrás', 'Mantén una postura natural y equilibrada, sin forzarla'],
    },
    deadlift: {
      src: 'assets/exercise-guides/deadlift-reference.png',
      alt: 'Ilustración de peso muerto con mancuernas: cadera hacia atrás, espalda neutra y peso cerca de las piernas.',
      stages: ['Pies firmes y peso cerca del cuerpo', 'Lleva la cadera atrás con espalda neutra', 'Empuja el suelo y extiende la cadera para subir'],
    },
    glute_bridge: {
      src: 'assets/exercise-guides/glute-bridge-reference.png',
      alt: 'Ilustración del puente de glúteos: acostado boca arriba con rodillas flexionadas, eleva y baja la pelvis.',
      stages: ['Acuéstate con rodillas flexionadas y pies apoyados', 'Eleva la pelvis apretando los glúteos, sin arquear la espalda', 'Baja la pelvis despacio y repite'],
    },
    calf_raise: {
      src: 'assets/exercise-guides/calf-raise-reference.png',
      alt: 'Ilustración de elevación de pantorrillas con mancuernas: de pie sobre una plataforma, eleva los talones y vuelve a bajar.',
      stages: ['Ponte erguido sobre una superficie firme', 'Eleva los talones y apóyate en la parte delantera del pie', 'Baja los talones lentamente; usa apoyo para equilibrarte'],
    },
    step_up: {
      src: 'assets/exercise-guides/step-up-reference.png',
      alt: 'Ilustración de subida al cajón: coloca un pie sobre un escalón firme, sube hasta quedar erguido y baja con control.',
      stages: ['Apoya todo el pie sobre un cajón firme y bajo', 'Empuja con esa pierna hasta quedar erguido arriba', 'Baja con control y alterna la pierna'],
    },
    jump_landing: {
      src: 'assets/exercise-guides/jump-landing-reference.png',
      alt: 'Ilustración de equilibrio sobre una pierna y control de la rodilla, como referencia para estabilizarse tras aterrizar.',
      stages: ['Haz un salto pequeño en un espacio despejado', 'Aterriza suave sobre ambos pies y flexiona las rodillas', 'Estabiliza el equilibrio antes de repetir'],
    },
    overhead_press: {
      src: 'assets/exercise-guides/overhead-press-reference.png',
      alt: 'Ilustración del press sobre la cabeza: lleva las pesas desde los hombros hasta arriba, con el tronco erguido.',
      stages: ['Sostén las pesas a la altura de los hombros', 'Empuja hacia arriba sin arquear la espalda', 'Baja con control hasta los hombros'],
    },
    biceps_curl: {
      src: 'assets/exercise-guides/biceps-curl-reference.png',
      alt: 'Ilustración del curl de bíceps con mancuernas: brazos a los lados y flexión alternada de un codo.',
      stages: ['Ponte erguido con las pesas junto a los muslos', 'Flexiona un codo sin mover el brazo ni balancear el cuerpo', 'Baja despacio y alterna el lado'],
    },
    row: {
      src: 'assets/exercise-guides/row-reference.png',
      alt: 'Ilustración de remo a una mano con apoyo en banco: espalda neutra y codo llevando la mancuerna hacia atrás.',
      stages: ['Apoya una mano y una rodilla en un banco firme', 'Con espalda neutra, lleva el codo hacia la cadera', 'Baja la pesa con control y cambia de lado'],
    },
    triceps_dip: {
      src: 'assets/exercise-guides/triceps-dip-reference.png',
      alt: 'Ilustración de fondos de tríceps en banco: manos apoyadas detrás, flexiona los codos para bajar y empuja para subir.',
      stages: ['Apoya las manos en un banco firme detrás de ti', 'Flexiona los codos y baja solo hasta un rango cómodo', 'Empuja con las manos y vuelve arriba con control'],
    },
    plank: {
      src: 'assets/exercise-guides/plank-reference.png',
      alt: 'Ilustración de plancha frontal sobre antebrazos: cabeza, espalda, cadera y piernas alineadas.',
      stages: ['Apoya antebrazos y puntas de los pies', 'Mantén cabeza, espalda y cadera alineadas', 'Respira; termina apoyando las rodillas con control'],
    },
    side_plank: {
      src: 'assets/exercise-guides/side-plank-reference.png',
      alt: 'Ilustración de plancha lateral apoyada en un antebrazo, con la cadera elevada y el cuerpo alineado.',
      stages: ['Apoya un antebrazo debajo del hombro', 'Eleva la cadera y alinea hombros, cadera y pies', 'Baja con control y repite del otro lado'],
    },
    crunch: {
      src: 'assets/exercise-guides/crunch-reference.png',
      alt: 'Ilustración de abdominales tipo crunch: tumbado con rodillas flexionadas, eleva hombros y parte alta de la espalda.',
      stages: ['Acuéstate con rodillas flexionadas y pies apoyados', 'Eleva hombros y espalda alta; no tires del cuello', 'Baja despacio hasta apoyar los hombros'],
    },
    burpee: {
      src: 'assets/exercise-guides/burpee-reference.png',
      alt: 'Secuencia de burpee: posición de pie, manos al suelo, plancha con flexión y regreso a pie con brazos arriba.',
      stages: ['De pie, baja y apoya las manos', 'Lleva los pies atrás a una plancha; la flexión es opcional', 'Acerca los pies y ponte de pie; el salto final es opcional'],
    },
    jumping_jack: {
      src: 'assets/exercise-guides/jumping-jack-reference.png',
      alt: 'Ilustración de jumping jacks: desde pies juntos y brazos abajo, separa los pies y eleva los brazos.',
      stages: ['Empieza de pie con pies juntos y brazos a los lados', 'Separa los pies y eleva los brazos al mismo tiempo', 'Vuelve al centro; puedes hacerlo dando pasos sin saltar'],
    },
    mountain_climber: {
      src: 'assets/exercise-guides/mountain-climber-reference.png',
      alt: 'Ilustración de escaladores: en plancha alta, lleva una rodilla hacia el pecho y alterna las piernas.',
      stages: ['Colócate en plancha alta, con manos bajo los hombros', 'Lleva una rodilla hacia el pecho sin subir demasiado la cadera', 'Regresa el pie y alterna despacio, manteniendo el tronco firme'],
    },
  };
  const mirroredExerciseArms = new Set(['arm_raise', 'jumping_jack', 'overhead_press']);
  const guidePose = (head, shoulder, elbow, hand, hip, knee, ankle) => ({
    head, shoulder, elbow, hand, hip, knee, ankle,
  });
  const exerciseIllustrationPoses = {
    standing: [
      guidePose([0, 27], [0, 54], [-15, 69], [-16, 89], [0, 103], [0, 145], [0, 180]),
      guidePose([0, 27], [0, 54], [-15, 69], [-16, 89], [0, 103], [0, 145], [0, 180]),
      guidePose([0, 27], [0, 54], [-15, 69], [-16, 89], [0, 103], [0, 145], [0, 180]),
    ],
    squat: [
      guidePose([0, 27], [0, 54], [-15, 69], [-16, 89], [0, 103], [0, 145], [0, 180]),
      guidePose([-8, 63], [0, 91], [-16, 106], [-1, 124], [12, 132], [29, 151], [32, 180]),
      guidePose([0, 27], [0, 54], [-15, 69], [-16, 89], [0, 103], [0, 145], [0, 180]),
    ],
    pushUp: [
      guidePose([-62, 129], [-38, 132], [-18, 147], [-2, 164], [15, 137], [48, 147], [80, 161]),
      guidePose([-62, 129], [-38, 132], [-19, 157], [-2, 164], [15, 137], [48, 147], [80, 161]),
      guidePose([-62, 129], [-38, 132], [-18, 147], [-2, 164], [15, 137], [48, 147], [80, 161]),
    ],
    lunge: [
      guidePose([0, 27], [0, 54], [-15, 69], [-16, 89], [0, 103], [0, 145], [0, 180]),
      guidePose([-5, 37], [0, 63], [-15, 78], [-16, 98], [7, 111], [34, 151], [35, 180]),
      guidePose([0, 27], [0, 54], [-15, 69], [-16, 89], [0, 103], [0, 145], [0, 180]),
    ],
    armRaise: [
      guidePose([0, 27], [0, 54], [-15, 69], [-16, 89], [0, 103], [0, 145], [0, 180]),
      guidePose([0, 27], [0, 54], [-24, 36], [-38, 22], [0, 103], [0, 145], [0, 180]),
      guidePose([0, 27], [0, 54], [-15, 69], [-16, 89], [0, 103], [0, 145], [0, 180]),
    ],
    mobility: [
      guidePose([0, 27], [0, 54], [-15, 69], [-16, 89], [0, 103], [0, 145], [0, 180]),
      guidePose([0, 27], [0, 54], [-25, 42], [-40, 35], [0, 103], [0, 145], [0, 180]),
      guidePose([0, 27], [0, 54], [-15, 69], [-16, 89], [0, 103], [0, 145], [0, 180]),
    ],
    hinge: [
      guidePose([0, 27], [0, 54], [-15, 69], [-16, 89], [0, 103], [0, 145], [0, 180]),
      guidePose([-16, 72], [-2, 91], [-11, 112], [6, 135], [17, 119], [8, 151], [8, 180]),
      guidePose([0, 27], [0, 54], [-15, 69], [-16, 89], [0, 103], [0, 145], [0, 180]),
    ],
    bridge: [
      guidePose([-60, 164], [-39, 166], [-26, 169], [-10, 174], [17, 169], [48, 158], [77, 180]),
      guidePose([-60, 164], [-39, 166], [-26, 169], [-10, 174], [17, 130], [48, 150], [77, 180]),
      guidePose([-60, 164], [-39, 166], [-26, 169], [-10, 174], [17, 169], [48, 158], [77, 180]),
    ],
    calfRaise: [
      guidePose([0, 27], [0, 54], [-15, 69], [-16, 89], [0, 103], [0, 145], [0, 180]),
      guidePose([0, 27], [0, 54], [-15, 69], [-16, 89], [0, 103], [0, 145], [-2, 169]),
      guidePose([0, 27], [0, 54], [-15, 69], [-16, 89], [0, 103], [0, 145], [0, 180]),
    ],
    stepUp: [
      guidePose([0, 27], [0, 54], [-15, 69], [-16, 89], [0, 103], [0, 145], [0, 180]),
      guidePose([-4, 33], [0, 59], [-15, 74], [-16, 94], [0, 108], [13, 144], [14, 162]),
      guidePose([0, 27], [0, 54], [-15, 69], [-16, 89], [0, 103], [0, 145], [0, 180]),
    ],
    landing: [
      guidePose([0, 27], [0, 54], [-15, 69], [-16, 89], [0, 103], [0, 145], [0, 180]),
      guidePose([-5, 61], [0, 88], [-20, 72], [-32, 56], [10, 126], [25, 153], [27, 180]),
      guidePose([-5, 61], [0, 88], [-20, 72], [-32, 56], [10, 126], [25, 153], [27, 180]),
    ],
    overheadPress: [
      guidePose([0, 27], [0, 54], [-18, 43], [-19, 25], [0, 103], [0, 145], [0, 180]),
      guidePose([0, 27], [0, 54], [-20, 35], [-20, 12], [0, 103], [0, 145], [0, 180]),
      guidePose([0, 27], [0, 54], [-18, 43], [-19, 25], [0, 103], [0, 145], [0, 180]),
    ],
    curl: [
      guidePose([0, 27], [0, 54], [-15, 69], [-16, 89], [0, 103], [0, 145], [0, 180]),
      guidePose([0, 27], [0, 54], [-23, 72], [-12, 51], [0, 103], [0, 145], [0, 180]),
      guidePose([0, 27], [0, 54], [-15, 69], [-16, 89], [0, 103], [0, 145], [0, 180]),
    ],
    row: [
      guidePose([-13, 69], [-2, 89], [-19, 106], [-34, 123], [17, 119], [8, 151], [8, 180]),
      guidePose([-13, 69], [-2, 89], [-2, 104], [13, 119], [17, 119], [8, 151], [8, 180]),
      guidePose([-13, 69], [-2, 89], [-19, 106], [-34, 123], [17, 119], [8, 151], [8, 180]),
    ],
    dip: [
      guidePose([-30, 75], [-10, 91], [8, 110], [14, 132], [10, 117], [28, 148], [30, 180]),
      guidePose([-30, 75], [-10, 91], [14, 104], [14, 132], [10, 128], [28, 153], [30, 180]),
      guidePose([-30, 75], [-10, 91], [8, 110], [14, 132], [10, 117], [28, 148], [30, 180]),
    ],
    plank: [
      guidePose([-62, 129], [-38, 132], [-25, 151], [-10, 168], [15, 137], [48, 147], [80, 161]),
      guidePose([-62, 129], [-38, 132], [-25, 151], [-10, 168], [15, 137], [48, 147], [80, 161]),
      guidePose([-62, 129], [-38, 132], [-25, 151], [-10, 168], [15, 137], [48, 147], [80, 161]),
    ],
    sidePlank: [
      guidePose([-62, 147], [-38, 150], [-25, 164], [-10, 178], [10, 145], [45, 154], [78, 162]),
      guidePose([-62, 147], [-38, 150], [-25, 164], [-10, 178], [10, 120], [45, 145], [78, 162]),
      guidePose([-62, 147], [-38, 150], [-25, 164], [-10, 178], [10, 145], [45, 154], [78, 162]),
    ],
    crunch: [
      guidePose([-70, 165], [-44, 166], [-28, 156], [-20, 143], [7, 169], [42, 149], [70, 180]),
      guidePose([-62, 143], [-39, 151], [-23, 143], [-18, 130], [7, 169], [42, 149], [70, 180]),
      guidePose([-70, 165], [-44, 166], [-28, 156], [-20, 143], [7, 169], [42, 149], [70, 180]),
    ],
    burpee: [
      guidePose([0, 27], [0, 54], [-15, 69], [-16, 89], [0, 103], [0, 145], [0, 180]),
      guidePose([-62, 129], [-38, 132], [-25, 151], [-10, 168], [15, 137], [48, 147], [80, 161]),
      guidePose([0, 27], [0, 54], [-15, 69], [-16, 89], [0, 103], [0, 145], [0, 180]),
    ],
    jumpingJack: [
      guidePose([0, 27], [0, 54], [-15, 69], [-16, 89], [0, 103], [0, 145], [0, 180]),
      guidePose([0, 27], [0, 54], [-29, 39], [-49, 26], [0, 103], [18, 145], [30, 180]),
      guidePose([0, 27], [0, 54], [-15, 69], [-16, 89], [0, 103], [0, 145], [0, 180]),
    ],
    mountainClimber: [
      guidePose([-62, 129], [-38, 132], [-25, 151], [-10, 168], [15, 137], [48, 147], [80, 161]),
      guidePose([-62, 129], [-38, 132], [-25, 151], [-10, 168], [15, 137], [25, 164], [80, 161]),
      guidePose([-62, 129], [-38, 132], [-25, 151], [-10, 168], [15, 137], [48, 147], [80, 161]),
    ],
  };
  const livePreviewIntervalMs = 100;
  const livePoseTransitionMs = 160;
  const exerciseSessionSampleIntervalMs = 500;
  const maxExerciseSessionFrames = 30;
  const poseConnections = [
    ['NOSE', 'LEFT_EYE_INNER'], ['LEFT_EYE_INNER', 'LEFT_EYE'], ['LEFT_EYE', 'LEFT_EYE_OUTER'], ['LEFT_EYE_OUTER', 'LEFT_EAR'],
    ['NOSE', 'RIGHT_EYE_INNER'], ['RIGHT_EYE_INNER', 'RIGHT_EYE'], ['RIGHT_EYE', 'RIGHT_EYE_OUTER'], ['RIGHT_EYE_OUTER', 'RIGHT_EAR'],
    ['MOUTH_LEFT', 'MOUTH_RIGHT'],
    ['LEFT_SHOULDER', 'RIGHT_SHOULDER'],
    ['LEFT_SHOULDER', 'LEFT_ELBOW'], ['LEFT_ELBOW', 'LEFT_WRIST'],
    ['LEFT_WRIST', 'LEFT_PINKY'], ['LEFT_WRIST', 'LEFT_INDEX'], ['LEFT_WRIST', 'LEFT_THUMB'], ['LEFT_PINKY', 'LEFT_INDEX'],
    ['RIGHT_SHOULDER', 'RIGHT_ELBOW'], ['RIGHT_ELBOW', 'RIGHT_WRIST'],
    ['RIGHT_WRIST', 'RIGHT_PINKY'], ['RIGHT_WRIST', 'RIGHT_INDEX'], ['RIGHT_WRIST', 'RIGHT_THUMB'], ['RIGHT_PINKY', 'RIGHT_INDEX'],
    ['LEFT_SHOULDER', 'LEFT_HIP'], ['RIGHT_SHOULDER', 'RIGHT_HIP'],
    ['LEFT_HIP', 'RIGHT_HIP'],
    ['LEFT_HIP', 'LEFT_KNEE'], ['LEFT_KNEE', 'LEFT_ANKLE'],
    ['RIGHT_HIP', 'RIGHT_KNEE'], ['RIGHT_KNEE', 'RIGHT_ANKLE'],
    ['LEFT_ANKLE', 'LEFT_HEEL'], ['LEFT_HEEL', 'LEFT_FOOT_INDEX'], ['LEFT_ANKLE', 'LEFT_FOOT_INDEX'],
    ['RIGHT_ANKLE', 'RIGHT_HEEL'], ['RIGHT_HEEL', 'RIGHT_FOOT_INDEX'], ['RIGHT_ANKLE', 'RIGHT_FOOT_INDEX'],
    ['LEFT_EAR', 'LEFT_SHOULDER'], ['RIGHT_EAR', 'RIGHT_SHOULDER'],
  ];

  let athletes = [];
  let selectedImage = null;
  let cameraStream = null;
  let cameraFacingMode = 'user';
  let cameraStartupInProgress = false;
  let exerciseSession = null;
  let livePreviewEnabled = false;
  let livePreviewTimer = null;
  let livePreviewInProgress = false;
  let livePreviewErrorNotified = false;
  let livePoseKeypoints = null;
  let livePoseAnimationFrame = null;
  let activeAssessment = null;
  let activeReportType = 'individual';
  let editAthleteId = null;
  let filteredAssessments = [];
  let imageObjectUrl = null;
  let scheduleMonth = new Date();

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    })[char]);
  }

  async function loadHistory() {
    const athleteId = $('#history-athlete')?.value;
    const timeline = $('#history-timeline');
    if (!timeline) return;
    const athlete = athletes.find(item => String(item.id) === String(athleteId));
    $('#history-athlete-avatar').textContent = athlete?.initials || '—';
    $('#history-athlete-name').textContent = athlete?.full_name || 'Selecciona atleta';
    $('#history-athlete-meta').textContent = athlete ? `ID #${athlete.id} · ${athlete.sport}` : '';
    if (!athleteId) {
      timeline.innerHTML = '<p class="text-sm text-gray">Selecciona un atleta para consultar su historial.</p>';
      return;
    }
    try {
      const response = await api.getAthleteAssessments(athleteId);
      const records = listFromResponse(response);
      timeline.innerHTML = records.length ? records.map(item => {
        const level = item.risk_level || 'low';
        return `<div style="position:relative"><div style="position:absolute;left:-1.85rem;top:.25rem;width:12px;height:12px;border-radius:50%;background:var(--primary);border:2px solid white"></div>
          <div class="card"><div class="card-body">
            <div class="flex justify-between items-center gap-2"><strong>Evaluación · ${escapeHtml(item.view_type_display || item.view_type)}</strong><span class="text-sm text-gray">${escapeHtml(formatDate(item.session_date))}</span></div>
            <p class="text-sm mt-2">Riesgo: ${escapeHtml(riskLabels[level] || level)} (${escapeHtml(item.risk_score ?? '—')}/100)</p>
            <p class="text-sm text-gray mt-1">${escapeHtml((item.detected_issues || []).map(issue => issue.description).join(' ') || 'Sin hallazgos reportados.')}</p>
            <button class="btn btn-outline btn-sm mt-3" data-assessment-action="download" data-assessment-id="${escapeHtml(item.id)}">Descargar PDF</button>
          </div></div></div>`;
      }).join('') : '<p class="text-sm text-gray">Este atleta todavía no tiene evaluaciones registradas.</p>';
      filteredAssessments = records;
    } catch (error) {
      showFailure(error);
    }
  }

  async function loadDashboard() {
    try {
      const stats = await api.getDashboardStats();
      $('#dashboard-athlete-count').textContent = stats.athletes?.total ?? 0;
      $('#dashboard-assessments-today').textContent = stats.assessments?.today ?? 0;
      $('#dashboard-active-alerts').textContent = stats.alerts?.active ?? 0;
      const alertNav = $$('.nav-item').find(item => item.textContent.includes('Alertas'));
      const navBadge = alertNav?.querySelector('.nav-badge');
      if (navBadge) navBadge.textContent = stats.alerts?.critical ?? 0;
      const alertsList = $('#recent-alerts-list');
      if (alertsList) {
        const recent = stats.alerts?.recent || [];
        alertsList.innerHTML = recent.length ? recent.map(alert => `
          <div class="alert ${alert.severity === 'critical' || alert.severity === 'high' ? 'alert-danger' : 'alert-warning'}">
            <div><strong class="text-sm">${escapeHtml(alert.title)}</strong><p class="text-xs mt-1">${escapeHtml(alert.description)}</p></div>
          </div>`).join('') : '<p class="text-sm text-gray">No hay alertas activas.</p>';
      }
      const recentAlerts = stats.alerts?.recent || [];
      $('#notification-count').textContent = `Notificaciones (${recentAlerts.length})`;
      const notifications = $('#notification-list');
      if (notifications) {
        notifications.innerHTML = recentAlerts.length ? recentAlerts.map(alert => `
          <button class="dropdown-item" style="flex-direction:column;align-items:flex-start;gap:.2rem;padding:.875rem 1rem;width:100%;text-align:left" onclick="navigate('alerts')">
            <strong class="text-sm">${escapeHtml(alert.title)}</strong>
            <span class="text-sm text-gray">${escapeHtml(alert.description)}</span>
          </button>`).join('') : '<p class="dropdown-item text-sm text-gray">Sin notificaciones nuevas.</p>';
      }
      const frequency = stats.zone_frequency || {};
      const zoneTotals = {
        knee: (frequency.knee_left || 0) + (frequency.knee_right || 0),
        shoulder: (frequency.shoulder_left || 0) + (frequency.shoulder_right || 0),
        hip: (frequency.hip_left || 0) + (frequency.hip_right || 0),
        ankle: (frequency.ankle_left || 0) + (frequency.ankle_right || 0),
        spine: (frequency.spine_lateral || 0) + (frequency.spine_sagittal || 0),
        elbow: (frequency.elbow_left || 0) + (frequency.elbow_right || 0),
      };
      const maximum = Math.max(1, ...Object.values(zoneTotals));
      $$('.bar-item[data-zone]').forEach(item => {
        const value = zoneTotals[item.dataset.zone] || 0;
        item.querySelector('.bar-value').textContent = value;
        item.querySelector('.bar-fill').style.height = `${Math.max(3, value / maximum * 100)}%`;
      });
      $$('[data-risk-zone]').forEach(item => {
        const value = zoneTotals[item.dataset.riskZone] || 0;
        const count = item.querySelector('.font-bold');
        if (count) count.textContent = value;
      });
    } catch (error) {
      showFailure(error);
    }
  }

  async function loadRiskSummary() {
    try {
      const summary = await api.getRiskSummary();
      const distribution = summary.distribution || {};
      const values = $$('#page-risk-analysis .grid-4 .stat-value');
      if (values[0]) values[0].textContent = distribution.high || 0;
      if (values[1]) values[1].textContent = distribution.medium || 0;
      if (values[2]) values[2].textContent = distribution.low || 0;
      if (values[3]) values[3].textContent = `${Math.round(summary.average_risk || 0)}/100`;
    } catch (error) {
      showFailure(error);
    }
  }

  function listFromResponse(response) {
    if (Array.isArray(response)) return response;
    if (response && Array.isArray(response.results)) return response.results;
    return [];
  }

  function errorMessage(error) {
    try {
      const data = JSON.parse(error.message);
      if (typeof data === 'string') return data;
      return Object.entries(data).map(([key, value]) => {
        const message = Array.isArray(value) ? value.join(' ') : String(value);
        return key === 'detail' || key === 'error' ? message : `${key}: ${message}`;
      }).join(' ');
    } catch {
      if (error.message === 'Failed to fetch') {
        return 'No se pudo conectar con el servidor. Verifica que la API esté activa y vuelve a intentar.';
      }
      return error.message || 'Ocurrió un error inesperado.';
    }
  }

  function setBusy(button, busy, label) {
    if (!button) return;
    button.disabled = busy;
    button.classList.toggle('loading', busy);
    if (busy) {
      button.dataset.originalHtml = button.innerHTML;
      button.textContent = label;
    } else if (button.dataset.originalHtml) {
      button.innerHTML = button.dataset.originalHtml;
      delete button.dataset.originalHtml;
    }
  }

  function showFailure(error) {
    showToast(errorMessage(error), 'error');
  }

  function riskBadge(level) {
    const badge = document.createElement('span');
    badge.className = `badge ${riskClasses[level] || 'badge-gray'}`;
    badge.textContent = riskLabels[level] || 'Sin evaluar';
    return badge;
  }

  function formatDate(value) {
    if (!value) return 'Sin evaluaciones';
    const date = /^\d{4}-\d{2}-\d{2}$/.test(value)
      ? new Date(`${value}T12:00:00`)
      : new Date(value);
    return Number.isNaN(date.getTime()) ? '—' : date.toLocaleDateString('es-MX');
  }

  function populateAthleteSelect() {
    $('#btn-retry-athletes')?.classList.add('hidden');
    ['#assessment-athlete', '#history-athlete', '#appointment-athlete'].forEach(selector => {
      const select = $(selector);
      if (!select) return;
      const current = select.value;
      select.replaceChildren(new Option(athletes.length ? 'Selecciona un atleta' : 'No hay atletas registrados', ''));
      athletes.forEach(athlete => {
        select.add(new Option(`${athlete.full_name || `${athlete.first_name} ${athlete.last_name}`} (#${athlete.id})`, athlete.id));
      });
      if (athletes.some(athlete => String(athlete.id) === current)) select.value = current;
    });
  }

  function showAthleteLoadError() {
    $('#btn-retry-athletes')?.classList.remove('hidden');
    ['#assessment-athlete', '#history-athlete', '#appointment-athlete'].forEach(selector => {
      const select = $(selector);
      if (!select) return;
      select.replaceChildren(new Option('Error al cargar atletas; vuelve a intentar', ''));
    });
  }

  function renderAthletes(records) {
    const tbody = $('#athletes-table-body');
    if (!tbody) return;
    tbody.replaceChildren();
    if (!records.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center text-gray">No hay atletas para mostrar.</td></tr>';
      return;
    }

    records.forEach(athlete => {
      const row = document.createElement('tr');
      const name = athlete.full_name || `${athlete.first_name} ${athlete.last_name}`;
      const gender = { M: 'M', F: 'F', O: 'Otro' }[athlete.gender] || '—';
      row.innerHTML = `
        <td><div class="flex items-center gap-2"><div class="avatar" style="width:36px;height:36px;font-size:.8rem">${escapeHtml(athlete.initials || name.split(' ').map(part => part[0]).slice(0, 2).join(''))}</div><div><div class="table-name">${escapeHtml(name)}</div><div class="text-xs text-gray">ID #${escapeHtml(athlete.id)}</div></div></div></td>
        <td class="text-sm text-gray">${escapeHtml(athlete.age ?? '—')} / ${escapeHtml(gender)}</td>
        <td class="text-sm">${escapeHtml(athlete.sport)}</td>
        <td></td>
        <td class="text-sm">${escapeHtml(athlete.assessments_count ?? 0)} sesiones</td>
        <td class="text-sm text-gray">${escapeHtml(formatDate(athlete.last_assessment_date))}</td>
        <td><div class="flex gap-1">
          <button class="btn btn-icon btn-ghost btn-sm" title="Ver historial" data-athlete-action="history" data-athlete-id="${escapeHtml(athlete.id)}">◉</button>
          <button class="btn btn-icon btn-ghost btn-sm" title="Evaluar postura" data-athlete-action="evaluate" data-athlete-id="${escapeHtml(athlete.id)}">＋</button>
          <button class="btn btn-icon btn-ghost btn-sm" title="Editar atleta" data-athlete-action="edit" data-athlete-id="${escapeHtml(athlete.id)}">✎</button>
        </div></td>`;
      row.children[3].appendChild(riskBadge(athlete.current_risk_level));
      tbody.appendChild(row);
    });
    renderRecentAthletes(records);
  }

  function renderRecentAthletes(records) {
    const tbody = $('#recent-athletes-body');
    if (!tbody) return;
    const recent = [...records].sort((a, b) => new Date(b.last_assessment_date || b.created_at) - new Date(a.last_assessment_date || a.created_at)).slice(0, 5);
    tbody.innerHTML = recent.length ? recent.map(athlete => `
      <tr><td><div class="flex items-center gap-2"><div class="avatar" style="width:32px;height:32px;font-size:.75rem">${escapeHtml(athlete.initials)}</div><span class="table-name">${escapeHtml(athlete.full_name)}</span></div></td><td class="text-gray text-sm">${escapeHtml(athlete.sport)}</td><td></td><td class="text-sm text-gray">${escapeHtml(formatDate(athlete.last_assessment_date))}</td></tr>
    `).join('') : '<tr><td colspan="4" class="text-sm text-gray">No hay atletas registrados.</td></tr>';
    recent.forEach((athlete, index) => {
      const row = tbody.rows[index];
      if (row) row.cells[2].appendChild(riskBadge(athlete.current_risk_level));
    });
  }

  async function loadAthletes(params = {}) {
    try {
      const response = await api.getAthletes(params);
      athletes = listFromResponse(response);
      populateAthleteSelect();
      renderAthletes(athletes);
      const count = $('#page-athletes p.text-sm.text-gray');
      if (count) count.textContent = `${response.count ?? athletes.length} atletas registrados`;
      return athletes;
    } catch (error) {
      showAthleteLoadError();
      showFailure(error);
      throw error;
    }
  }

  function readAthleteForm() {
    const payload = {
      first_name: $('#athlete-first-name').value.trim(),
      last_name: $('#athlete-last-name').value.trim(),
      sport: $('#athlete-sport').value,
      gender: $('#athlete-gender').value,
      date_of_birth: $('#athlete-date-of-birth').value || null,
      email: $('#athlete-email').value.trim() || null,
      weight_kg: $('#athlete-weight').value || null,
      height_cm: $('#athlete-height').value || null,
      previous_injuries: $('#athlete-injuries').value.trim(),
    };
    return Object.fromEntries(Object.entries(payload).filter(([, value]) => value !== null));
  }

  function clearAthleteForm() {
    ['athlete-first-name', 'athlete-last-name', 'athlete-date-of-birth', 'athlete-gender',
      'athlete-weight', 'athlete-height', 'athlete-sport', 'athlete-email', 'athlete-injuries']
      .forEach(id => { $(`#${id}`).value = ''; });
    editAthleteId = null;
    $('#btn-create-athlete').textContent = 'Registrar Atleta';
  }

  async function saveAthlete() {
    const button = $('#btn-create-athlete');
    const wasEditing = Boolean(editAthleteId);
    if (!$('#athlete-first-name').value.trim() || !$('#athlete-last-name').value.trim() || !$('#athlete-sport').value) {
      showToast('Completa nombre, apellido y deporte.', 'warning');
      return;
    }
    setBusy(button, true, 'Guardando...');
    try {
      const payload = readAthleteForm();
      if (editAthleteId) await api.updateAthlete(editAthleteId, payload);
      else await api.createAthlete(payload);
      closeModal('modal-add-athlete');
      clearAthleteForm();
      await loadAthletes();
      showToast(wasEditing ? 'Atleta actualizado.' : 'Atleta registrado.', 'success');
    } catch (error) {
      showFailure(error);
    } finally {
      setBusy(button, false);
    }
  }

  function setPreview(imageFile) {
    exerciseSession = null;
    updateAnalyzeButton();
    selectedImage = imageFile;
    activeAssessment = null;
    const video = $('#camera-video');
    const image = $('#camera-image');
    stopCamera();
    video.style.display = 'none';
    image.style.display = 'block';
    $('#camera-placeholder').style.display = 'none';
    $('#pose-live-status').style.display = 'none';
    if (imageObjectUrl) URL.revokeObjectURL(imageObjectUrl);
    imageObjectUrl = URL.createObjectURL(imageFile);
    image.src = imageObjectUrl;
    image.onload = () => {
      if (activeAssessment?.keypoints_data) drawPose(activeAssessment.keypoints_data);
    };
    clearPoseOverlay();
    $('#pose-legend').style.display = 'none';
    $('#analysis-result').style.display = 'none';
  }

  function stopCamera() {
    stopLivePreview();
    if (cameraStream) {
      cameraStream.getTracks().forEach(track => track.stop());
      cameraStream = null;
    }
    const video = $('#camera-video');
    if (video) video.srcObject = null;
    const button = $('#btn-start-camera');
    if (button) button.textContent = 'Iniciar Cámara';
    updateAnalyzeButton();
  }

  function updateAnalyzeButton() {
    const button = $('#btn-analyze');
    if (!button || button.disabled) return;
    if (exerciseSession) {
      button.textContent = `Finalizar ejercicio · ${exerciseSession.frames.length}`;
      return;
    }
    button.textContent = cameraStream ? 'Iniciar ejercicio' : 'Analizar con IA';
  }

  function updateExerciseGuide() {
    const select = $('#assessment-exercise');
    const title = $('#exercise-guide-title');
    const camera = $('#exercise-guide-camera');
    const tip = $('#exercise-guide-tip');
    const steps = $('#exercise-guide-steps');
    const illustration = $('#exercise-guide-illustration');
    if (!select || !title || !camera || !tip || !steps || !illustration) return;

    const guide = exerciseGuides[select.value] || exerciseGuides.general;
    const exerciseName = select.selectedOptions[0]?.textContent.trim().replace(/^\d+\.\s*/, '');
    title.textContent = `Ejemplo: ${exerciseName || 'Ejercicio seleccionado'}`;
    camera.textContent = guide.camera;
    tip.textContent = guide.tip;
    const poseGroup = exerciseIllustrationGroups[select.value] || 'standing';
    const reference = exerciseReferenceImages[select.value];
    illustration.innerHTML = reference
      ? renderExerciseReference(reference)
      : renderExerciseIllustration(
        exerciseName || 'ejercicio',
        exerciseIllustrationPoses[poseGroup],
        mirroredExerciseArms.has(select.value),
      );
    steps.replaceChildren(...guide.steps.map(instruction => {
      const step = document.createElement('li');
      step.textContent = instruction;
      return step;
    }));
  }

  function renderExerciseReference(reference) {
    const stages = reference.stages
      .map((stage, index) => `<span><strong>${index + 1}</strong>${escapeHtml(stage)}</span>`)
      .join('');
    return `<figure class="exercise-guide-reference">
      <img src="${reference.src}" alt="${escapeHtml(reference.alt)}" loading="lazy" decoding="async">
      <figcaption>${stages}</figcaption>
    </figure>`;
  }

  function renderExerciseIllustration(exerciseName, poses, mirrorArms) {
    const centers = [100, 300, 500];
    const labels = ['1 · INICIO', '2 · MOVIMIENTO', '3 · REGRESO'];
    const point = (center, coords, dx = 0) => `${center + coords[0] + dx},${coords[1]}`;
    const line = (center, first, second, third, dx = 0) =>
      `M${point(center, first, dx)} L${point(center, second, dx)} L${point(center, third, dx)}`;
    const figures = poses.map((pose, index) => {
      const center = centers[index];
      const limb = (path, tone = 'near') =>
        `<path class="guide-limb-outline" d="${path}"/><path class="guide-limb guide-limb-${tone}" d="${path}"/>`;
      const legs = [-5, 5].map((offset, legIndex) =>
        limb(line(center, pose.hip, pose.knee, pose.ankle, offset), legIndex ? 'near' : 'far'),
      ).join('');
      const arms = [-1, 1].map((side, armIndex) => {
        const offset = side * 4;
        const armPoint = (coords, dx) => `${center + (mirrorArms && armIndex ? -coords[0] : coords[0]) + dx},${coords[1]}`;
        const path = `M${armPoint(pose.shoulder, offset)} L${armPoint(pose.elbow, offset)} L${armPoint(pose.hand, offset)}`;
        return limb(path, armIndex ? 'near' : 'far');
      }).join('');
      const feet = [-5, 5].map((offset, footIndex) => {
        const [x, y] = pose.ankle;
        const tone = footIndex ? 'guide-shoe' : 'guide-shoe guide-shoe-far';
        return `<path class="${tone}" d="M${center + x + offset - 5},${y - 2} q4,-2 8,1 l9,4 q3,2 1,5 h-17 q-4,-1 -2,-5z"/>`;
      }).join('');
      const neckX = center + pose.head[0] * .35;
      const neckY = pose.head[1] + 10;
      return `
        <g aria-hidden="true">
          <ellipse class="guide-shadow" cx="${center}" cy="190" rx="48" ry="6"/>
          <line class="guide-floor" x1="${center - 78}" y1="196" x2="${center + 78}" y2="196"/>
          ${legs}
          <path class="guide-neck" d="M${neckX - 4},${neckY - 5} L${neckX + 4},${neckY - 5} L${neckX + 5},${pose.shoulder[1] + 6} L${neckX - 5},${pose.shoulder[1] + 6}z"/>
          <path class="guide-torso-outline" d="M${point(center, pose.shoulder, -10)} Q${point(center, pose.shoulder, 0)} ${point(center, pose.shoulder, 10)} L${point(center, pose.hip, 10)} Q${point(center, pose.hip, 0)} ${point(center, pose.hip, -10)}z"/>
          <path class="guide-torso" d="M${point(center, pose.shoulder, -8)} Q${point(center, pose.shoulder, 0)} ${point(center, pose.shoulder, 8)} L${point(center, pose.hip, 8)} Q${point(center, pose.hip, 0)} ${point(center, pose.hip, -8)}z"/>
          <path class="guide-shirt-detail" d="M${point(center, pose.shoulder, -7)} Q${point(center, pose.shoulder, 0)} ${point(center, pose.shoulder, 7)}"/>
          ${arms}
          <path class="guide-shorts-outline" d="M${center + pose.hip[0] - 12},${pose.hip[1] - 2} Q${center + pose.hip[0]},${pose.hip[1] + 3} ${center + pose.hip[0] + 12},${pose.hip[1] - 2} L${center + pose.hip[0] + 13},${pose.hip[1] + 17} L${center + pose.hip[0] + 3},${pose.hip[1] + 19} L${center + pose.hip[0]},${pose.hip[1] + 10} L${center + pose.hip[0] - 5},${pose.hip[1] + 19} L${center + pose.hip[0] - 14},${pose.hip[1] + 16}z"/>
          ${feet}
          <circle class="guide-head" cx="${center + pose.head[0]}" cy="${pose.head[1]}" r="11"/>
          <path class="guide-hair" d="M${center + pose.head[0] - 10},${pose.head[1] - 1} C${center + pose.head[0] - 14},${pose.head[1] - 15} ${center + pose.head[0] + 5},${pose.head[1] - 17} ${center + pose.head[0] + 10},${pose.head[1] - 7} Q${center + pose.head[0] + 3},${pose.head[1] - 11} ${center + pose.head[0] - 1},${pose.head[1] - 4} Q${center + pose.head[0] - 5},${pose.head[1] - 1} ${center + pose.head[0] - 10},${pose.head[1] - 1}z"/>
          <circle class="guide-eye" cx="${center + pose.head[0] + 4}" cy="${pose.head[1] + 1}" r="1.2"/>
          <circle class="guide-joint" cx="${center + pose.elbow[0] + 4}" cy="${pose.elbow[1]}" r="3.2"/>
          <circle class="guide-joint" cx="${center + pose.knee[0] + 5}" cy="${pose.knee[1]}" r="3.8"/>
        </g>
        <text class="guide-stage" x="${center}" y="218">${labels[index]}</text>`;
    }).join('');

    return `<svg viewBox="0 0 600 228" role="img" aria-label="Secuencia ilustrada para ${escapeHtml(exerciseName)}">
      <defs><marker id="exercise-guide-arrow" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto"><path d="M0 0 L6 3.5 L0 7" fill="none" stroke="#60a5fa" stroke-width="1.5"/></marker></defs>
      <rect class="guide-panel" x="7" y="7" width="186" height="214" rx="14"/>
      <rect class="guide-panel" x="207" y="7" width="186" height="214" rx="14"/>
      <rect class="guide-panel" x="407" y="7" width="186" height="214" rx="14"/>
      <path class="guide-arrow" d="M184 92 H213" marker-end="url(#exercise-guide-arrow)"/>
      <path class="guide-arrow" d="M384 92 H413" marker-end="url(#exercise-guide-arrow)"/>
      ${figures}
    </svg>`;
  }

  function updateCameraSwitchButton() {
    const button = $('#btn-switch-camera');
    if (!button) return;
    button.classList.toggle('is-mobile-visible', isMobileCameraDevice());
    const nextFacingMode = cameraFacingMode === 'user' ? 'environment' : 'user';
    const nextCameraLabel = nextFacingMode === 'environment' ? 'trasera' : 'frontal';
    button.textContent = `Usar cámara ${nextCameraLabel}`;
    button.setAttribute('aria-label', `Usar cámara ${nextCameraLabel}`);
  }

  function isMobileCameraDevice() {
    const compactViewport = window.matchMedia('(max-width: 768px)').matches;
    const touchViewport = navigator.maxTouchPoints > 0
      && window.matchMedia('(max-width: 1024px)').matches;
    return compactViewport || touchViewport;
  }

  async function requestCameraStream(facingMode, mobileCamera = isMobileCameraDevice()) {
    const cameraLabels = facingMode === 'environment'
      ? /back|rear|environment|trasera|posterior/i
      : /front|frontal|delantera|user/i;
    let cameras = [];
    if (navigator.mediaDevices.enumerateDevices) {
      try {
        cameras = await navigator.mediaDevices.enumerateDevices();
      } catch (error) {
        if (error.name !== 'NotAllowedError' && error.name !== 'SecurityError') throw error;
      }
    }
    const matchingCamera = cameras.find(device =>
      device.kind === 'videoinput' && device.deviceId && cameraLabels.test(device.label),
    );
    const video = {
      width: { ideal: mobileCamera ? 640 : 1280 },
      height: { ideal: mobileCamera ? 480 : 960 },
      frameRate: { ideal: mobileCamera ? 24 : 30, max: 30 },
    };
    if (matchingCamera) {
      video.deviceId = { exact: matchingCamera.deviceId };
    } else {
      video.facingMode = { ideal: facingMode };
    }

    const stream = await navigator.mediaDevices.getUserMedia({ audio: false, video });
    const track = stream.getVideoTracks()[0];
    const actualFacingMode = track?.getSettings().facingMode;
    if (actualFacingMode && actualFacingMode !== facingMode) {
      stream.getTracks().forEach(mediaTrack => mediaTrack.stop());
      throw new Error(`El navegador mantuvo la cámara ${actualFacingMode === 'user' ? 'frontal' : 'trasera'}.`);
    }
    return stream;
  }

  function cameraErrorMessage(error, facingMode) {
    if (error?.name === 'NotAllowedError' || error?.name === 'PermissionDeniedError') {
      return 'Permite el acceso a la cámara en los ajustes del navegador y vuelve a intentarlo.';
    }
    if (error?.name === 'NotFoundError' || error?.name === 'OverconstrainedError') {
      return `No se encontró una cámara ${facingMode === 'environment' ? 'trasera' : 'frontal'} disponible.`;
    }
    if (error?.name === 'NotReadableError' || error?.name === 'AbortError') {
      return 'La cámara sigue ocupada. Cierra otras aplicaciones que la usen y vuelve a intentarlo.';
    }
    return error?.message || 'Verifica los permisos y que la cámara no esté siendo usada por otra aplicación.';
  }

  function stopLivePreview() {
    livePreviewEnabled = false;
    if (livePreviewTimer) {
      clearTimeout(livePreviewTimer);
      livePreviewTimer = null;
    }
  }

  function setLiveStatus(message, state) {
    const status = $('#pose-live-status');
    status.className = `pose-live-status${state ? ` is-${state}` : ''}`;
    $('#pose-live-message').textContent = message;
    status.style.display = 'flex';
  }

  function capturePreviewFrame() {
    const video = $('#camera-video');
    if (!cameraStream || !video.videoWidth || !video.videoHeight) return Promise.resolve(null);
    const canvas = document.createElement('canvas');
    const targetWidth = isMobileCameraDevice() ? 480 : 640;
    const scale = Math.min(1, targetWidth / video.videoWidth);
    canvas.width = Math.round(video.videoWidth * scale);
    canvas.height = Math.round(video.videoHeight * scale);
    const context = canvas.getContext('2d');
    if (!context) return Promise.reject(new Error('No se pudo preparar el fotograma de cámara.'));
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    return new Promise((resolve, reject) => {
      canvas.toBlob(blob => {
        if (!blob) {
          reject(new Error('No se pudo capturar el fotograma de cámara.'));
          return;
        }
        resolve(new File([blob], `prevenia-preview-${Date.now()}.jpg`, { type: 'image/jpeg' }));
      }, 'image/jpeg', isMobileCameraDevice() ? 0.62 : 0.75);
    });
  }

  function startLivePreview() {
    livePreviewEnabled = true;
    const analyzeFrame = async () => {
      if (!livePreviewEnabled || !cameraStream || livePreviewInProgress) return;
      livePreviewInProgress = true;
      try {
        const frame = await capturePreviewFrame();
        if (!frame || !livePreviewEnabled) return;
        const exerciseType = $('#assessment-exercise').value;
        const viewType = $('#assessment-view-type').value;
        const result = await api.analyzePosePreview(frame, exerciseType, viewType);
        if (!livePreviewEnabled || !cameraStream) return;
        livePreviewErrorNotified = false;
        if (!result?.success) {
          clearPoseOverlay();
          setLiveStatus(result?.error || 'No se detecta el cuerpo completo. Ajusta la cámara.', 'warning');
        } else {
          collectExerciseFrame(frame);
          animateLivePose(result.keypoints_data, result);
          const exerciseFeedback = result.exercise_feedback;
          if (exerciseFeedback) {
            const hasExerciseIssue = exerciseFeedback.status === 'warning';
            setLiveStatus(
              [exerciseFeedback.summary, exerciseFeedback.cues[0]]
                .filter((message, index, messages) => message && messages.indexOf(message) === index)
                .join(' '),
              hasExerciseIssue ? 'warning' : exerciseFeedback.status === 'neutral' ? 'pending' : '',
            );
            return;
          }
          const hasDeviation = (result.joint_angles || []).some(angle => angle.is_within_normal === false)
            || (result.detected_issues || []).length > 0;
          setLiveStatus(
            hasDeviation ? 'Desviación detectada: revisa los puntos rojos.' : 'Postura dentro de los rangos medidos.',
            hasDeviation ? 'warning' : '',
          );
        }
      } catch (error) {
        setLiveStatus(`No se pudo analizar este fotograma. Reintentando: ${errorMessage(error)}`, 'warning');
        if (!livePreviewErrorNotified) {
          showFailure(error);
          livePreviewErrorNotified = true;
        }
      } finally {
        livePreviewInProgress = false;
        if (livePreviewEnabled && cameraStream) {
          livePreviewTimer = window.setTimeout(analyzeFrame, livePreviewIntervalMs);
        }
      }
    };
    analyzeFrame();
  }

  function clearPoseOverlay() {
    if (livePoseAnimationFrame !== null) {
      cancelAnimationFrame(livePoseAnimationFrame);
      livePoseAnimationFrame = null;
    }
    livePoseKeypoints = null;
    const canvas = $('#posture-canvas');
    const context = canvas.getContext('2d');
    context.clearRect(0, 0, canvas.width, canvas.height);
  }

  function animateLivePose(keypoints, assessment) {
    if (livePoseAnimationFrame !== null) {
      cancelAnimationFrame(livePoseAnimationFrame);
      livePoseAnimationFrame = null;
    }

    const target = keypoints || {};
    const from = livePoseKeypoints || target;
    const startedAt = performance.now();
    const transitionDuration = isMobileCameraDevice() ? 100 : livePoseTransitionMs;

    const animate = now => {
      const progress = Math.min(1, (now - startedAt) / transitionDuration);
      const easedProgress = 1 - (1 - progress) ** 3;
      const interpolated = {};

      Object.entries(target).forEach(([name, destination]) => {
        const origin = from[name] || destination;
        interpolated[name] = {
          x: origin.x + (destination.x - origin.x) * easedProgress,
          y: origin.y + (destination.y - origin.y) * easedProgress,
          z: origin.z + (destination.z - origin.z) * easedProgress,
          visibility: destination.visibility,
        };
      });

      livePoseKeypoints = interpolated;
      drawPose(interpolated, assessment);
      if (progress < 1) {
        livePoseAnimationFrame = requestAnimationFrame(animate);
      } else {
        livePoseAnimationFrame = null;
      }
    };

    livePoseAnimationFrame = requestAnimationFrame(animate);
  }

  async function startCamera() {
    if (cameraStartupInProgress) return false;
    if (cameraStream) {
      if (exerciseSession) return finishExerciseSession();
      stopCamera();
      $('#camera-video').style.display = 'none';
      $('#camera-placeholder').style.display = 'flex';
      $('#pose-legend').style.display = 'none';
      $('#pose-live-status').style.display = 'none';
      return false;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      showToast('La cámara requiere HTTPS o localhost y un navegador compatible. Puedes cargar una imagen.', 'error');
      return false;
    }
    cameraStartupInProgress = true;
    const startButton = $('#btn-start-camera');
    const switchButton = $('#btn-switch-camera');
    if (startButton) startButton.disabled = true;
    if (switchButton) switchButton.disabled = true;
    try {
      selectedImage = null;
      activeAssessment = null;
      $('#analysis-result').style.display = 'none';
      const mobileCamera = isMobileCameraDevice();
      cameraStream = await requestCameraStream(cameraFacingMode, mobileCamera);
      const video = $('#camera-video');
      video.srcObject = cameraStream;
      await video.play();
      video.style.display = 'block';
      $('#camera-image').style.display = 'none';
      $('#camera-placeholder').style.display = 'none';
      clearPoseOverlay();
      $('#pose-legend').style.display = 'none';
      setLiveStatus('Cámara activa. Analizando postura...', 'pending');
      startButton.textContent = 'Detener Cámara';
      updateAnalyzeButton();
      startLivePreview();
      showToast('Cámara lista. Los puntos y alertas se actualizarán en vivo; pulsa Analizar para guardar el resultado.', 'info');
      return true;
    } catch (error) {
      cameraStream?.getTracks().forEach(track => track.stop());
      cameraStream = null;
      const video = $('#camera-video');
      if (video)       video.srcObject = null;
      if (startButton) startButton.textContent = 'Iniciar Cámara';
      updateAnalyzeButton();
      showToast(`No se pudo abrir la cámara: ${cameraErrorMessage(error, cameraFacingMode)}`, 'error');
      return false;
    } finally {
      cameraStartupInProgress = false;
      if (startButton) startButton.disabled = false;
      if (switchButton) switchButton.disabled = false;
    }
  }

  function collectExerciseFrame(frame) {
    if (!exerciseSession || exerciseSession.frames.length >= maxExerciseSessionFrames) return;
    const now = performance.now();
    if (now - exerciseSession.lastFrameAt < exerciseSessionSampleIntervalMs) return;
    exerciseSession.frames.push(frame);
    exerciseSession.lastFrameAt = now;
    updateAnalyzeButton();
    setLiveStatus(
      `Ejercicio en curso · ${exerciseSession.frames.length} fotogramas analizados.`,
      'pending',
    );
    if (exerciseSession.frames.length === maxExerciseSessionFrames) {
      setLiveStatus(
        'Límite de fotogramas alcanzado. Finaliza el ejercicio para ver las estadísticas.',
        'warning',
      );
    }
  }

  function startExerciseSession() {
    const athleteId = $('#assessment-athlete').value;
    if (!athleteId) {
      showToast('Selecciona un atleta antes de iniciar el ejercicio.', 'warning');
      return;
    }
    exerciseSession = {
      frames: [],
      startedAt: Date.now(),
      lastFrameAt: 0,
    };
    $('#analysis-result').style.display = 'none';
    updateAnalyzeButton();
    setLiveStatus('Ejercicio listo. Comienza el movimiento; recopilaré fotogramas durante la sesión.', 'pending');
    showToast('Recopilación iniciada. Al terminar el ejercicio, pulsa «Finalizar ejercicio».', 'info');
  }

  async function finishExerciseSession() {
    if (!exerciseSession) return;
    const session = exerciseSession;
    const durationSeconds = Math.max(1, Math.round((Date.now() - session.startedAt) / 1000));
    if (session.frames.length < 3) {
      showToast('Mantén el cuerpo visible y continúa hasta recopilar al menos 3 fotogramas.', 'warning');
      return;
    }

    exerciseSession = null;
    stopLivePreview();
    setPreview(session.frames[session.frames.length - 1]);
    const button = $('#btn-analyze');
    setBusy(button, true, `Analizando ${session.frames.length} fotogramas...`);
    $('#analysis-status').textContent = 'Analizando sesión...';
    $('#analysis-result-body').innerHTML = `
      <p class="text-sm text-gray">Evaluando ${session.frames.length} fotogramas del ejercicio y consolidando estadísticas...</p>`;
    $('#analysis-result').style.display = 'block';

    try {
      const response = await api.analyzeExerciseSession(
        session.frames,
        $('#assessment-athlete').value,
        $('#assessment-exercise').value,
        $('#assessment-view-type').value,
        durationSeconds,
      );
      if (!response?.success || !response.assessment) {
        throw new Error(response?.error || 'No se pudo analizar la sesión. Intenta de nuevo con el cuerpo completo en cámara.');
      }
      renderAnalysis(response);
      loadAssessments().catch(showFailure);
      loadAthletes().catch(showFailure);
      loadAlerts().catch(showFailure);
      loadDashboard();
    } catch (error) {
      $('#analysis-result').style.display = 'none';
      showFailure(error);
    } finally {
      setBusy(button, false);
      updateAnalyzeButton();
    }
  }

  async function switchCamera() {
    if (!isMobileCameraDevice() || cameraStartupInProgress) return;
    const previousFacingMode = cameraFacingMode;
    cameraFacingMode = previousFacingMode === 'user' ? 'environment' : 'user';
    updateCameraSwitchButton();
    if (!cameraStream) return;

    stopCamera();
    $('#camera-video').style.display = 'none';
    $('#camera-placeholder').style.display = 'flex';
    clearPoseOverlay();
    await new Promise(resolve => window.setTimeout(resolve, 300));
    const switched = await startCamera();
    if (switched) return;

    cameraFacingMode = previousFacingMode;
    updateCameraSwitchButton();
    const restored = await startCamera();
    if (restored) {
      showToast('No se pudo cambiar de cámara. Se restauró la cámara anterior.', 'info');
    }
  }

  function captureVideoFrame() {
    const video = $('#camera-video');
    if (!cameraStream || !video.videoWidth || !video.videoHeight) return Promise.resolve(null);
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    return new Promise((resolve, reject) => {
      canvas.toBlob(blob => {
        if (!blob) {
          reject(new Error('No se pudo capturar el fotograma de la cámara.'));
          return;
        }
        resolve(new File([blob], `prevenia-${Date.now()}.jpg`, { type: 'image/jpeg' }));
      }, 'image/jpeg', 0.92);
    });
  }

  async function chooseImage() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/jpeg,image/png,image/webp';
    input.onchange = () => {
      const file = input.files?.[0];
      if (!file) return;
      if (!file.type.startsWith('image/')) {
        showToast('Selecciona un archivo de imagen válido.', 'error');
        return;
      }
      if (file.size > 15 * 1024 * 1024) {
        showToast('La imagen supera el límite de 15 MB.', 'error');
        return;
      }
      setPreview(file);
      showToast('Imagen lista. Selecciona el atleta e inicia el análisis.', 'success');
    };
    input.click();
  }

  function drawPose(keypoints, assessment = activeAssessment) {
    const canvas = $('#posture-canvas');
    const source = $('#camera-image').style.display !== 'none' ? $('#camera-image') : $('#camera-video');
    if (!keypoints || !source || !source.clientWidth) return;
    const rect = canvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const ratio = isMobileCameraDevice()
      ? Math.min(window.devicePixelRatio || 1, 1.25)
      : window.devicePixelRatio || 1;
    const reduceCanvasEffects = isMobileCameraDevice();
    const pixelWidth = Math.round(rect.width * ratio);
    const pixelHeight = Math.round(rect.height * ratio);
    if (canvas.width !== pixelWidth || canvas.height !== pixelHeight) {
      canvas.width = pixelWidth;
      canvas.height = pixelHeight;
    }
    const context = canvas.getContext('2d');
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, rect.width, rect.height);

    const sourceWidth = source.naturalWidth || source.videoWidth;
    const sourceHeight = source.naturalHeight || source.videoHeight;
    if (!sourceWidth || !sourceHeight) return;
    const scale = Math.max(rect.width / sourceWidth, rect.height / sourceHeight);
    const offsetX = (rect.width - sourceWidth * scale) / 2;
    const offsetY = (rect.height - sourceHeight * scale) / 2;
    const point = (name, minVisibility = 0.35) => {
      const value = keypoints[name];
      if (!value || value.visibility < minVisibility) return null;
      return {
        x: offsetX + value.x * sourceWidth * scale,
        y: offsetY + value.y * sourceHeight * scale,
      };
    };

    context.lineWidth = Math.max(2, rect.width / 180);
    context.lineCap = 'round';
    context.lineJoin = 'round';
    const flaggedLandmarks = new Set();
    const exerciseFeedback = assessment?.exercise_feedback;
    (exerciseFeedback?.issues || []).forEach(issue => {
      (issue.landmarks || []).forEach(name => flaggedLandmarks.add(name));
    });
    const landmarkGroups = {
      knee_left: ['LEFT_HIP', 'LEFT_KNEE', 'LEFT_ANKLE'],
      knee_right: ['RIGHT_HIP', 'RIGHT_KNEE', 'RIGHT_ANKLE'],
      hip_left: ['LEFT_SHOULDER', 'LEFT_HIP', 'LEFT_KNEE'],
      hip_right: ['RIGHT_SHOULDER', 'RIGHT_HIP', 'RIGHT_KNEE'],
      shoulder_left: ['LEFT_ELBOW', 'LEFT_SHOULDER', 'LEFT_HIP'],
      shoulder_right: ['RIGHT_ELBOW', 'RIGHT_SHOULDER', 'RIGHT_HIP'],
      elbow_left: ['LEFT_SHOULDER', 'LEFT_ELBOW', 'LEFT_WRIST'],
      elbow_right: ['RIGHT_SHOULDER', 'RIGHT_ELBOW', 'RIGHT_WRIST'],
      ankle_left: ['LEFT_KNEE', 'LEFT_ANKLE', 'LEFT_HEEL', 'LEFT_FOOT_INDEX'],
      ankle_right: ['RIGHT_KNEE', 'RIGHT_ANKLE', 'RIGHT_HEEL', 'RIGHT_FOOT_INDEX'],
      spine_lateral: ['LEFT_SHOULDER', 'RIGHT_SHOULDER', 'LEFT_HIP', 'RIGHT_HIP'],
    };
    if (!exerciseFeedback) {
      (assessment?.joint_angles || []).forEach(angle => {
        if (angle.is_within_normal === false) {
          (landmarkGroups[angle.joint] || []).forEach(name => flaggedLandmarks.add(name));
        }
      });
      (assessment?.detected_issues || []).forEach(issue => {
        if (issue.type === 'valgus_knee') {
        const side = issue.zone?.toLowerCase().includes('izquierda') ? 'left' : 'right';
        (landmarkGroups[`knee_${side}`] || []).forEach(name => flaggedLandmarks.add(name));
        } else if (issue.type === 'hip_asymmetry') {
          ['LEFT_HIP', 'RIGHT_HIP'].forEach(name => flaggedLandmarks.add(name));
        } else if (issue.type === 'shoulder_asymmetry') {
          ['LEFT_SHOULDER', 'RIGHT_SHOULDER'].forEach(name => flaggedLandmarks.add(name));
        } else if (issue.type === 'lateral_deviation') {
          landmarkGroups.spine_lateral.forEach(name => flaggedLandmarks.add(name));
        }
      });
    }
    poseConnections.forEach(([start, end]) => {
      const a = point(start, 0.2);
      const b = point(end, 0.2);
      if (!a || !b) return;
      context.beginPath();
      context.moveTo(a.x, a.y);
      context.lineTo(b.x, b.y);
      context.strokeStyle = 'rgba(8, 18, 32, .8)';
      context.lineWidth = Math.max(5, rect.width / 105);
      context.stroke();
      context.beginPath();
      context.moveTo(a.x, a.y);
      context.lineTo(b.x, b.y);
      context.strokeStyle = flaggedLandmarks.has(start) || flaggedLandmarks.has(end) ? '#ff3b4f' : '#38f2a2';
      context.lineWidth = Math.max(2.5, rect.width / 210);
      context.shadowColor = context.strokeStyle;
      context.shadowBlur = reduceCanvasEffects ? 0 : Math.max(5, rect.width / 110);
      context.stroke();
    });
    Object.keys(keypoints).forEach(name => {
      const p = point(name);
      if (!p) return;
      const color = flaggedLandmarks.has(name) ? '#ff3b4f' : '#38f2a2';
      const radius = Math.max(4, rect.width / 115);
      context.shadowColor = color;
      context.shadowBlur = reduceCanvasEffects ? 0 : radius * 1.8;
      context.beginPath();
      context.arc(p.x, p.y, radius, 0, Math.PI * 2);
      context.fillStyle = color;
      context.fill();
      context.shadowBlur = 0;
      context.beginPath();
      context.arc(p.x, p.y, radius * 0.42, 0, Math.PI * 2);
      context.fillStyle = '#f8fffc';
      context.fill();
    });
  }

  function renderAnalysis(result) {
    const assessment = result.assessment;
    activeAssessment = assessment;
    const risk = assessment.risk_level || 'low';
    $('#risk-score').textContent = Math.round(assessment.risk_score ?? 0);
    const level = $('#risk-level');
    level.textContent = riskLabels[risk] || risk;
    level.className = `badge ${riskClasses[risk] || 'badge-gray'}`;
    $('#risk-confidence').textContent = assessment.ai_confidence == null ? '—' : `${assessment.ai_confidence}%`;
    $('#analysis-status').textContent = `Completado · ${formatDate(assessment.session_date)}`;

    const body = $('#analysis-result-body');
    body.innerHTML = `
      <div id="analysis-session-statistics"></div>
      <div id="analysis-issues"></div>
      <div id="analysis-exercise-feedback"></div>
      <h4 class="font-semibold mb-3" style="color:var(--gray-700)">Recomendaciones del sistema:</h4>
      <div id="analysis-recommendations" style="display:flex;flex-direction:column;gap:.5rem"></div>
      <div class="flex gap-2 mt-4">
        <button class="btn btn-primary btn-sm" id="btn-download-assessment">Descargar PDF</button>
        <button class="btn btn-outline btn-sm" id="btn-view-assessments">Ver historial</button>
      </div>`;
    const exerciseFeedback = assessment.exercise_feedback;
    const sessionStatistics = exerciseFeedback?.session_statistics;
    const hasRiskRange = Number.isFinite(sessionStatistics?.average_risk_score)
      && Number.isFinite(sessionStatistics?.peak_risk_score);
    const sessionRiskSummary = hasRiskRange
      ? `<p class="text-sm mt-1">Riesgo promedio: ${escapeHtml(Number(sessionStatistics.average_risk_score).toFixed(1))}/100 · Pico de riesgo: ${escapeHtml(Number(sessionStatistics.peak_risk_score).toFixed(1))}/100</p>`
      : Number.isFinite(sessionStatistics?.risk_score)
        ? `<p class="text-sm mt-1">Riesgo estimado: ${escapeHtml(Number(sessionStatistics.risk_score).toFixed(1))}/100 · Calidad de seguimiento: ${escapeHtml(sessionStatistics.tracking_quality ?? '—')}%</p>`
        : '';
    $('#analysis-session-statistics').innerHTML = sessionStatistics
      ? `<div class="alert alert-info mb-4">
          <div><strong>Resumen de la sesión</strong>
          <p class="text-sm mt-1">${escapeHtml(sessionStatistics.frames_analyzed)} fotogramas analizados · ${escapeHtml(sessionStatistics.duration_seconds)} s</p>
          ${sessionRiskSummary}
          <p class="text-sm mt-1">${escapeHtml(sessionStatistics.repeated_findings)} hallazgos recurrentes durante el ejercicio</p>
          </div>
        </div>`
      : '';
    const issues = (assessment.detected_issues || []).filter(issue => issue.type !== 'exercise_form');
    $('#analysis-issues').innerHTML = issues.length
      ? issues.map(issue => `<div class="alert ${['high', 'critical'].includes(issue.severity) ? 'alert-warning' : 'alert-info'} mb-3"><div><strong>${escapeHtml(issue.zone || 'Hallazgo')}</strong><p class="text-sm mt-1">${escapeHtml(issue.description)}</p></div></div>`).join('')
      : exerciseFeedback?.status === 'warning'
        ? ''
        : '<div class="alert alert-success mb-4"><div>El análisis no detectó desviaciones relevantes.</div></div>';
    $('#analysis-exercise-feedback').innerHTML = exerciseFeedback
      ? `<div class="alert ${exerciseFeedback.status === 'warning' ? 'alert-warning' : 'alert-info'} mb-3">
          <div><strong>Técnica · ${escapeHtml(exerciseFeedback.exercise_display)}</strong>
          <p class="text-sm mt-1">${escapeHtml(exerciseFeedback.summary)}</p>
          ${(exerciseFeedback.cues || []).filter(cue => cue !== exerciseFeedback.summary).map(cue => `<p class="text-sm mt-1">${escapeHtml(cue)}</p>`).join('')}
          </div>
        </div>`
      : '';
    const recommendations = assessment.recommendations || [];
    $('#analysis-recommendations').innerHTML = recommendations.length
      ? recommendations.map(item => `<p class="text-sm">✓ ${escapeHtml(item)}</p>`).join('')
      : '<p class="text-sm text-gray">No hay recomendaciones disponibles.</p>';

    const angles = assessment.joint_angles || [];
    $('#joint-readings').innerHTML = angles.length
      ? angles.map(angle => {
        const range = angle.normal_range || normalRanges[angle.joint];
        const normal = angle.is_within_normal !== false;
        const percent = Math.min(100, Math.max(3, Math.abs(angle.deviation_from_normal || 0) * 5));
        const color = normal ? 'green' : (risk === 'critical' || risk === 'high' ? 'red' : 'amber');
        return `<div class="joint-item">
          <div class="joint-name">${escapeHtml(angle.joint_display || jointLabels[angle.joint] || angle.joint)}</div>
          <div class="joint-value"><span class="joint-angle">${escapeHtml(Number(angle.angle_degrees).toFixed(1))}°</span><span class="badge ${normal ? 'risk-low' : riskClasses[risk] || 'risk-medium'}">${normal ? 'Normal' : 'Fuera de rango'}</span></div>
          <div class="progress-bar"><div class="progress-fill ${color}" style="width:${percent}%"></div></div>
          <div class="text-xs text-gray mt-1">${range ? `Rango normal: ${range[0]}°–${range[1]}°` : 'Rango no definido'}</div>
        </div>`;
      }).join('')
      : '<p class="text-sm text-gray">El análisis no devolvió ángulos articulares.</p>';
    $('#analysis-result').style.display = 'block';
    $('#pose-legend').style.display = 'flex';
    $('#analysis-result').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    drawPose(assessment.keypoints_data, assessment);
    const hasDeviation = exerciseFeedback
      ? exerciseFeedback.status === 'warning'
      : (assessment.joint_angles || []).some(angle => angle.is_within_normal === false)
        || (assessment.detected_issues || []).length > 0;
    if (hasDeviation) {
      showToast('Alerta postural: se detectaron puntos fuera del rango normal. Revisa la sección de Alertas.', 'warning');
    } else {
      showToast(`Análisis completado. Riesgo ${riskLabels[risk] || risk.toLowerCase()}; postura dentro de los rangos medidos.`, 'success');
    }
  }

  async function handleExerciseAnalysis() {
    if (!cameraStream) return analyzePosture();
    if (exerciseSession) return finishExerciseSession();
    startExerciseSession();
  }

  async function analyzePosture() {
    const button = $('#btn-analyze');
    const athleteId = $('#assessment-athlete').value;
    if (!athleteId) {
      showToast('Selecciona un atleta antes de analizar.', 'warning');
      return;
    }

    let imageFile = selectedImage;
    try {
      if (cameraStream) {
        imageFile = await captureVideoFrame();
        if (!imageFile) throw new Error('La cámara aún no está lista; espera a que aparezca la imagen.');
        setPreview(imageFile);
      }
      if (!imageFile) {
        showToast('Activa la cámara o carga una imagen para iniciar el análisis.', 'warning');
        return;
      }
      setBusy(button, true, 'Analizando imagen...');
      $('#analysis-status').textContent = 'Procesando...';
      $('#analysis-result-body').innerHTML = '<p class="text-sm text-gray">Procesando la imagen y calculando ángulos...</p>';
      $('#analysis-result').style.display = 'block';
      const response = await api.analyzeImage(
        imageFile,
        athleteId,
        $('#assessment-view-type').value,
        $('#assessment-exercise').value,
      );
      if (!response?.success || !response.assessment) {
        throw new Error(response?.error || 'No se pudo detectar una postura. Asegúrate de mostrar el cuerpo completo.');
      }
      renderAnalysis(response);
      loadAssessments().catch(showFailure);
      loadAthletes().catch(showFailure);
      loadAlerts().catch(showFailure);
      loadDashboard();
    } catch (error) {
      $('#analysis-result').style.display = 'none';
      showFailure(error);
    } finally {
      setBusy(button, false);
    }
  }

  function drawPrintableReport(title, sections) {
    const popup = window.open('', '_blank');
    if (!popup) {
      showToast('Permite las ventanas emergentes para imprimir el reporte.', 'error');
      return;
    }
    writePrintableReport(popup, title, sections);
  }

  function writePrintableReport(popup, title, sections) {
    const content = sections.map(([heading, value]) => `
      <section><h2>${escapeHtml(heading)}</h2><pre>${escapeHtml(typeof value === 'string' ? value : JSON.stringify(value, null, 2))}</pre></section>
    `).join('');
    popup.document.write(`<!doctype html><html lang="es"><head><meta charset="utf-8"><title>${escapeHtml(title)}</title>
      <style>body{font:15px Arial,sans-serif;color:#172033;max-width:900px;margin:40px auto;padding:0 24px}h1{color:#123b74}h2{border-bottom:1px solid #ccd3df;padding-bottom:8px}pre{white-space:pre-wrap;font:14px Arial,sans-serif;line-height:1.5}section{margin:24px 0}@media print{body{margin:15mm auto}}</style>
      </head><body><h1>${escapeHtml(title)}</h1>${content}<script>window.onload=()=>window.print()<\/script></body></html>`);
    popup.document.close();
  }

  async function downloadAssessmentPDF(assessment) {
    if (!assessment?.id) throw new Error('No se encontró el identificador de la evaluación.');
    const pdf = await api.getAssessmentPDF(assessment.id);
    const url = URL.createObjectURL(pdf);
    const link = document.createElement('a');
    link.href = url;
    link.download = `prevenia-evaluacion-${assessment.id}.pdf`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    showToast('Reporte PDF descargado.', 'success');
  }

  function renderAssessments(records) {
    filteredAssessments = records;
    const pending = $('#tab-pending .grid');
    if (pending) {
      const waiting = records.filter(item => item.status === 'pending' || item.status === 'failed');
      pending.innerHTML = waiting.length ? waiting.map(item => `
        <div class="card"><div class="card-body">
          <div class="flex justify-between items-start mb-3"><div><div class="font-semibold">${escapeHtml(item.athlete_name)}</div><div class="text-xs text-gray">${escapeHtml(item.view_type_display || item.view_type)}</div></div><span class="badge ${item.status === 'failed' ? 'badge-red' : 'badge-amber'}">${escapeHtml(item.status_display || item.status)}</span></div>
          <p class="text-sm text-gray mb-3">${escapeHtml(item.error_message || item.notes || 'Evaluación pendiente de análisis.')}</p>
          <button class="btn btn-primary btn-sm w-full" data-assessment-action="analyze" data-assessment-id="${escapeHtml(item.id)}">Analizar</button>
        </div></div>`).join('') : '<p class="text-sm text-gray">No hay evaluaciones pendientes.</p>';
    }
    const completedBody = $('#tab-completed tbody');
    if (completedBody) {
      const completed = records.filter(item => item.status === 'completed');
      completedBody.innerHTML = completed.length ? completed.map(item => `
        <tr><td class="text-sm">${escapeHtml(formatDate(item.session_date))}</td><td class="table-name">${escapeHtml(item.athlete_name)}</td><td class="text-sm">${escapeHtml(item.view_type_display || item.view_type)}</td><td></td><td class="text-sm text-gray">${escapeHtml((item.joint_angles || []).map(angle => angle.joint_display).join(', ') || '—')}</td><td><span class="badge badge-green">Completada</span></td><td><button class="btn btn-outline btn-sm" data-assessment-action="download" data-assessment-id="${escapeHtml(item.id)}">Descargar PDF</button></td></tr>
      `).join('') : '<tr><td colspan="7" class="text-sm text-gray">Todavía no hay evaluaciones completadas.</td></tr>';
      completed.forEach((item, index) => {
        const row = completedBody.rows[index];
        if (row) row.cells[3].appendChild(riskBadge(item.risk_level));
      });
    }
    const completedCount = records.filter(item => item.status === 'completed').length;
    const pendingCount = records.filter(item => item.status === 'pending' || item.status === 'failed').length;
    const flagged = records.filter(item => ['high', 'critical'].includes(item.risk_level));
    const tabButtons = $$('.tab-btn');
    if (tabButtons[0]) tabButtons[0].textContent = `Pendientes (${pendingCount})`;
    if (tabButtons[1]) tabButtons[1].textContent = `Completadas (${completedCount})`;
    if (tabButtons[2]) tabButtons[2].textContent = `Marcadas (${flagged.length})`;
    const flaggedContainer = $('#flagged-assessments');
    if (flaggedContainer) {
      flaggedContainer.innerHTML = flagged.length ? flagged.map(item => `
        <div class="card"><div class="card-body">
          <div class="flex justify-between items-start"><strong>${escapeHtml(item.athlete_name)}</strong><span class="badge ${riskClasses[item.risk_level] || 'badge-gray'}">${escapeHtml(riskLabels[item.risk_level])}</span></div>
          <p class="text-sm text-gray mt-2">${escapeHtml(formatDate(item.session_date))} · ${escapeHtml(item.view_type_display || item.view_type)} · ${escapeHtml(item.risk_score ?? '—')}/100</p>
          <button class="btn btn-outline btn-sm mt-3" data-assessment-action="print" data-assessment-id="${escapeHtml(item.id)}">Ver evaluación</button>
        </div></div>`).join('') : '<p class="text-sm text-gray">No hay evaluaciones de riesgo alto o crítico.</p>';
    }
  }

  async function loadAssessments() {
    const response = await api.getAssessments();
    const records = listFromResponse(response);
    renderAssessments(records);
    return records;
  }

  function renderAlerts(records) {
    const container = $('#alerts-container');
    if (!container) return;
    if (!records.length) {
      container.innerHTML = '<div class="card"><div class="card-body text-sm text-gray">No hay alertas activas.</div></div>';
      return;
    }
    container.innerHTML = records.map(alert => `
      <div class="card"><div class="card-body"><div class="flex items-start gap-3">
        <div class="stat-icon ${alert.severity === 'critical' || alert.severity === 'high' ? 'red' : 'amber'}" style="flex-shrink:0">!</div>
        <div class="flex-1"><div class="flex justify-between items-start"><div><strong>${escapeHtml(alert.title)}</strong> <span class="badge ${riskClasses[alert.severity] || 'badge-gray'}">${escapeHtml(alert.severity_display || riskLabels[alert.severity] || alert.severity)}</span></div><span class="text-xs text-gray">${escapeHtml(formatDate(alert.created_at))}</span></div>
        <p class="text-sm text-gray mt-1">${escapeHtml(alert.description)}</p>
        ${alert.recommended_action ? `<p class="text-sm mt-2"><strong>Acción recomendada:</strong> ${escapeHtml(alert.recommended_action)}</p>` : ''}
        <div class="flex gap-2 mt-3"><button class="btn btn-ghost btn-sm" data-alert-action="read" data-alert-id="${escapeHtml(alert.id)}" ${alert.is_read ? 'disabled' : ''}>${alert.is_read ? 'Revisada' : 'Marcar como revisada'}</button><button class="btn btn-primary btn-sm" data-alert-action="resolve" data-alert-id="${escapeHtml(alert.id)}">Resolver</button></div></div>
      </div></div></div>`).join('');
  }

  async function loadAlerts() {
    const response = await api.getAlerts({ is_resolved: false });
    renderAlerts(listFromResponse(response));
  }

  function renderReports(records) {
    const container = $('#reports-list');
    if (!container) return;
    container.innerHTML = records.length ? records.map(report => `
      <div class="flex justify-between items-center py-2" style="border-bottom:1px solid var(--gray-100)">
        <div><strong class="text-sm">${escapeHtml(report.title)}</strong><div class="text-xs text-gray">${escapeHtml(report.report_type_display || report.report_type)} · ${escapeHtml(formatDate(report.created_at))} · ${escapeHtml(report.status_display || report.status)}</div></div>
        <button class="btn btn-outline btn-sm" data-report-action="download" data-report-id="${escapeHtml(report.id)}">Abrir / imprimir</button>
      </div>`).join('') : '<p class="text-sm text-gray">Aún no se han generado reportes.</p>';
  }

  async function loadReports() {
    const response = await api.getReports();
    renderReports(listFromResponse(response));
  }

  async function generateReport() {
    const athleteId = $('#assessment-athlete').value || (athletes[0] && athletes[0].id) || null;
    if (activeReportType === 'individual' && !athleteId) {
      showToast('Registra o selecciona un atleta para generar su reporte individual.', 'warning');
      return;
    }
    const button = $('#btn-generate-report');
    const popup = window.open('', '_blank');
    if (!popup) {
      showToast('Permite las ventanas emergentes para imprimir el reporte.', 'error');
      return;
    }
    setBusy(button, true, 'Generando...');
    try {
      const report = await api.generateReport(activeReportType, activeReportType === 'individual' ? athleteId : null);
      await loadReports();
      writePrintableReport(popup, report.title || 'Reporte PrevenIA', [
        ['Tipo de reporte', report.report_type_display || report.report_type],
        ['Datos', report.data_snapshot || {}],
      ]);
      showToast('Reporte generado. Usa Imprimir para guardarlo como PDF.', 'success');
    } catch (error) {
      popup.close();
      showFailure(error);
    } finally {
      setBusy(button, false);
    }
  }

  function updateProfileForm(user) {
    const form = $('#profile-form');
    if (!form) return;
    ['first_name', 'last_name', 'email', 'phone', 'institution', 'specialty'].forEach(field => {
      const input = $(`[name="${field}"]`, form);
      if (input) input.value = user[field] || '';
    });
  }

  async function loadProfile() {
    try {
      const user = await api.getProfile();
      updateProfileForm(user);
    } catch (error) {
      showFailure(error);
    }
  }

  async function saveProfile(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = Object.fromEntries(new FormData(form).entries());
    try {
      const user = await api.updateProfile(payload);
      const fullName = user.full_name || `${user.first_name} ${user.last_name}`.trim();
      localStorage.setItem('prevenia_user', JSON.stringify({ ...user, name: fullName }));
      $('#user-display-name').textContent = fullName || user.email;
      showToast('Perfil actualizado.', 'success');
    } catch (error) {
      showFailure(error);
    }
  }

  async function changePassword(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form).entries());
    try {
      await api.changePassword(values.old_password, values.new_password);
      form.reset();
      showToast('Contraseña actualizada.', 'success');
    } catch (error) {
      showFailure(error);
    }
  }

  function loadSettings() {
    const saved = JSON.parse(localStorage.getItem('prevenia_settings') || '{}');
    $$('#page-settings input, #page-settings select').forEach((input, index) => {
      const key = input.type === 'checkbox' ? `notification_${index}` : `setting_${index}`;
      if (Object.prototype.hasOwnProperty.call(saved, key)) {
        if (input.type === 'checkbox') input.checked = saved[key];
        else input.value = saved[key];
      }
      input.dataset.settingKey = key;
    });
    const save = $('#page-settings .btn-primary');
    if (save) save.addEventListener('click', () => {
      const values = {};
      $$('#page-settings input, #page-settings select').forEach(input => {
        values[input.dataset.settingKey] = input.type === 'checkbox' ? input.checked : input.value;
      });
      localStorage.setItem('prevenia_settings', JSON.stringify(values));
      showToast('Preferencias guardadas en este dispositivo.', 'success');
    });
  }

  function searchAthletes() {
    const search = $('#page-athletes .search-box input');
    const topSearch = $('#topbar-search input');
    const sport = $('#athlete-sport-filter');
    const risk = $('#athlete-risk-filter');
    let timer;
    const run = () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        const params = {};
        const name = (search?.value || topSearch?.value || '').trim();
        if (name) params.search = name;
        if (sport?.value) params.sport = sport.value;
        if (risk?.value) params.risk_level = risk.value.toLowerCase();
        loadAthletes(params).catch(() => {});
      }, 250);
    };
    search?.addEventListener('input', run);
    topSearch?.addEventListener('input', run);
    sport?.addEventListener('change', run);
    risk?.addEventListener('change', run);
  }

  async function handleClick(event) {
    const target = event.target.closest('button, [data-report-type]');
    if (!target) return;
    if (target.id === 'btn-start-camera') return startCamera();
    if (target.id === 'btn-switch-camera') return switchCamera();
    if (target.id === 'btn-upload-img') return chooseImage();
    if (target.id === 'btn-analyze') return handleExerciseAnalysis();
    if (target.id === 'btn-retry-athletes') {
      target.disabled = true;
      target.textContent = 'Cargando...';
      loadAthletes()
        .catch(() => {})
        .finally(() => {
          target.disabled = false;
          target.textContent = 'Reintentar carga';
        });
      return;
    }
    if (target.id === 'btn-create-athlete') return saveAthlete();
    if (target.id === 'btn-generate-report') return generateReport();
    if (target.id === 'btn-mark-all-alerts-read') {
      try {
        await api.markAllAlertsRead();
        await loadAlerts();
        showToast('Todas las alertas se marcaron como revisadas.', 'success');
      } catch (error) { showFailure(error); }
      return;
    }
    if (target.id === 'btn-download-assessment') {
      if (activeAssessment) {
        try {
          await downloadAssessmentPDF(activeAssessment);
        } catch (error) { showFailure(error); }
      }
      return;
    }
    if (target.id === 'btn-view-assessments') {
      navigate('assessments');
      return;
    }
    if (target.dataset.reportType) {
      activeReportType = target.dataset.reportType;
      $$('.card[data-report-type]').forEach(card => card.style.outline = card === target ? '2px solid var(--primary)' : '');
      showToast(`Seleccionado: ${target.querySelector('h3')?.textContent || 'reporte'}. Pulsa Generar Reporte.`, 'info');
      return;
    }
    if (target.dataset.athleteAction) {
      const athleteId = target.dataset.athleteId;
      if (target.dataset.athleteAction === 'evaluate') {
        $('#assessment-athlete').value = athleteId;
        navigate('posture');
      } else if (target.dataset.athleteAction === 'edit') {
        const athlete = athletes.find(item => String(item.id) === athleteId);
        if (!athlete) return;
        editAthleteId = athlete.id;
        $('#athlete-first-name').value = athlete.first_name || '';
        $('#athlete-last-name').value = athlete.last_name || '';
        $('#athlete-date-of-birth').value = athlete.date_of_birth || '';
        $('#athlete-gender').value = athlete.gender || '';
        $('#athlete-weight').value = athlete.weight_kg || '';
        $('#athlete-height').value = athlete.height_cm || '';
        $('#athlete-sport').value = athlete.sport || '';
        $('#athlete-email').value = athlete.email || '';
        $('#athlete-injuries').value = athlete.previous_injuries || '';
        $('#btn-create-athlete').textContent = 'Guardar cambios';
        openModal('modal-add-athlete');
      } else {
        $('#history-athlete').value = athleteId;
        navigate('history');
      }
      return;
    }
    if (target.dataset.alertAction) {
      const id = target.dataset.alertId;
      try {
        if (target.dataset.alertAction === 'resolve') await api.resolveAlert(id);
        else await api.patch(`/assessments/alerts/${id}/`, { is_read: true });
        await loadAlerts();
        showToast('Alerta actualizada.', 'success');
      } catch (error) { showFailure(error); }
      return;
    }
    if (target.dataset.assessmentAction) {
      const assessment = filteredAssessments.find(item => String(item.id) === target.dataset.assessmentId);
      if (assessment && target.dataset.assessmentAction === 'download') {
        try {
          await downloadAssessmentPDF(assessment);
        } catch (error) { showFailure(error); }
      }
      if (assessment && target.dataset.assessmentAction === 'analyze') {
        if (assessment.athlete) $('#assessment-athlete').value = assessment.athlete;
        if (assessment.view_type) $('#assessment-view-type').value = assessment.view_type;
        navigate('posture');
        showToast('Carga una imagen o usa la cámara para analizar esta evaluación.', 'info');
      }
      return;
    }
    if (target.dataset.reportAction === 'download') {
      const popup = window.open('', '_blank');
      if (!popup) {
        showToast('Permite las ventanas emergentes para imprimir el reporte.', 'error');
        return;
      }
      try {
        const response = await api.downloadReport(target.dataset.reportId);
        if (response.download_url) popup.location.href = response.download_url;
        else writePrintableReport(popup, 'Reporte PrevenIA', [['Datos', response.data || response]]);
      } catch (error) {
        popup.close();
        showFailure(error);
      }
    }
  }

  function loadAppointments() {
    const container = $('#appointments-list');
    if (!container) return;
    let records = [];
    try {
      records = JSON.parse(localStorage.getItem('prevenia_appointments') || '[]');
    } catch {
      localStorage.removeItem('prevenia_appointments');
    }
    const month = scheduleMonth.getMonth();
    const year = scheduleMonth.getFullYear();
    const monthRecords = records.filter(item => {
      const date = new Date(`${item.date}T12:00:00`);
      return date.getMonth() === month && date.getFullYear() === year;
    }).sort((a, b) => `${a.date} ${a.time}`.localeCompare(`${b.date} ${b.time}`));
    $('#schedule-current-month').textContent = scheduleMonth.toLocaleDateString('es-MX', { month: 'long', year: 'numeric' });
    container.innerHTML = monthRecords.length ? '' : '<p class="text-sm text-gray">No hay citas para este mes.</p>';
    monthRecords.forEach(item => {
      const row = document.createElement('div');
      row.dataset.localAppointment = item.id;
      row.style.cssText = 'display:flex;gap:1rem;align-items:center;padding:.875rem;background:var(--gray-50);border-radius:var(--radius);border-left:4px solid var(--gray-300)';
      row.innerHTML = `<div style="min-width:60px;text-align:center"><div class="text-sm font-bold">${escapeHtml(item.date)}</div><div class="text-sm text-gray">${escapeHtml(item.time)}</div></div><div class="flex-1"><div class="font-semibold">${escapeHtml(item.athlete)}</div><div class="text-sm text-gray">${escapeHtml(item.type)}${item.notes ? ` — ${escapeHtml(item.notes)}` : ''}</div></div><span class="badge badge-blue">${escapeHtml(item.priority)}</span><button class="btn btn-outline btn-sm" data-appointment-action="delete" data-appointment-id="${escapeHtml(item.id)}">Eliminar</button>`;
      container.appendChild(row);
    });
  }

  function saveAppointment() {
    const form = $('#modal-add-appointment');
    const inputs = $$('input, select, textarea', form);
    const athleteId = inputs[0].value;
    const athleteRecord = athletes.find(item => String(item.id) === String(athleteId));
    const athlete = athleteRecord?.full_name || '';
    const date = inputs[1].value;
    const time = inputs[2].value;
    const type = inputs[3].value;
    const priority = inputs[4].value;
    const notes = inputs[5].value.trim();
    if (!athleteId || !athlete || !date || !time) {
      showToast('Selecciona atleta, fecha y hora para agendar la cita.', 'warning');
      return;
    }
    let records = [];
    try {
      records = JSON.parse(localStorage.getItem('prevenia_appointments') || '[]');
    } catch {
      localStorage.removeItem('prevenia_appointments');
    }
    const id = `${Date.now()}`;
    records.push({ id, athlete, date, time, type, priority, notes });
    localStorage.setItem('prevenia_appointments', JSON.stringify(records));
    scheduleMonth = new Date(`${date}T12:00:00`);
    loadAppointments();
    closeModal('modal-add-appointment');
    showToast('Cita guardada en este dispositivo.', 'success');
  }

  async function handleAppointmentDelete(button) {
    const id = button.dataset.appointmentId;
    let records = [];
    try {
      records = JSON.parse(localStorage.getItem('prevenia_appointments') || '[]');
    } catch {
      localStorage.removeItem('prevenia_appointments');
    }
    records = records.filter(item => item.id !== id);
    localStorage.setItem('prevenia_appointments', JSON.stringify(records));
    button.closest('[data-local-appointment]')?.remove();
    showToast('Cita eliminada.', 'success');
  }

  function init() {
    if (!localStorage.getItem('prevenia_token')) {
      window.location.replace('login.html');
      return;
    }
    document.addEventListener('click', event => {
      const appointmentDelete = event.target.closest('[data-appointment-action="delete"]');
      if (appointmentDelete) handleAppointmentDelete(appointmentDelete);
      else handleClick(event);
    });
    $('#modal-add-athlete .btn-ghost')?.addEventListener('click', clearAthleteForm);
    $('#modal-add-appointment .btn-primary')?.addEventListener('click', saveAppointment);
    $('#profile-form')?.addEventListener('submit', saveProfile);
    $('#password-form')?.addEventListener('submit', changePassword);
    $('#history-athlete')?.addEventListener('change', loadHistory);
    $('#assessment-exercise')?.addEventListener('change', updateExerciseGuide);
    $('#schedule-prev-month')?.addEventListener('click', () => {
      scheduleMonth.setMonth(scheduleMonth.getMonth() - 1);
      loadAppointments();
    });
    $('#schedule-next-month')?.addEventListener('click', () => {
      scheduleMonth.setMonth(scheduleMonth.getMonth() + 1);
      loadAppointments();
    });
    searchAthletes();
    loadSettings();
    loadAppointments();
    renderAthletes([]);
    updateExerciseGuide();
    $('#joint-readings').innerHTML = '<p class="text-sm text-gray">Los ángulos aparecerán después del análisis.</p>';
    $('#history-timeline').innerHTML = '<p class="text-sm text-gray">Selecciona un atleta para consultar su historial.</p>';
    loadAthletes().catch(showFailure);
    loadDashboard();

    const originalNavigate = window.navigate;
    window.navigate = function (page) {
      originalNavigate(page);
      if (page === 'assessments') loadAssessments().catch(showFailure);
      if (page === 'alerts') loadAlerts().catch(showFailure);
      if (page === 'reports') loadReports().catch(showFailure);
      if (page === 'profile') loadProfile();
      if (page === 'schedule') loadAppointments();
      if (page === 'history') loadHistory();
      if (page === 'risk-analysis') loadRiskSummary();
    };
    window.addEventListener('resize', () => {
      updateCameraSwitchButton();
      if (activeAssessment?.keypoints_data) drawPose(activeAssessment.keypoints_data);
    });
    updateCameraSwitchButton();
    window.addEventListener('pagehide', stopCamera);
  }

  document.addEventListener('DOMContentLoaded', init);

  /* =====================================================================
   *  MÓDULO BIOMECÁNICO – Evaluación en tiempo real con OpenCV/MediaPipe
   *  Integrado con el backend de PrevenIA (Django REST)
   * ===================================================================== */

  // ── Thresholds (configurables por el médico) ─────────────────────────────
  const DEFAULT_THRESHOLDS = {
    valgus: 12,         // grados máx valgo rodilla
    trunk: 40,          // inclinación máx tronco
    squatDepth: 95,     // ángulo mín cadera en sentadilla
    pushupElbow: 90,    // ángulo mín codo en flexión
    asymmetry: 10,      // % diferencia bilateral máx
    framesDebounce: 3,  // fotogramas mínimos para confirmar error
  };
  let biomechThresholds = { ...DEFAULT_THRESHOLDS };

  // ── Estado de la sesión biomecánica ──────────────────────────────────────
  let biomechSession = null;   // null = sin sesión activa
  /*  biomechSession = {
        athleteId, athleteName, exerciseKey, exerciseLabel,
        startedAt, pausedAt, pausedTotalMs,
        isRunning, isPaused,
        events: [],          // errores agrupados
        rawEvents: [],       // línea cronológica
        frameCount: 0, goodFrames: 0,
        lastAngleSnapshot: {},
        savedAssessmentId: null,
      } */

  let biomechStopwatchTimer = null;
  let biomechRequestFrame    = null;
  let biomechVideoCanvas     = null; // canvas auxiliar para captura
  let biomechCurrentKps      = null; // keypoints suavizados actuales
  let biomechEmaKps          = null; // acumulador EMA
  const EMA_ALPHA            = 0.35; // factor EMA (0=muy suavizado, 1=raw)
  const BIOMECH_CAPTURE_MS   = 120;  // ms entre capturas enviadas a la API
  let biomechLastCapture     = 0;
  let biomechFpsCounter      = { frames: 0, lastTs: 0, fps: 0 };

  const EXERCISE_LABELS = {
    squat:         'Sentadilla',
    push_up:       'Flexión de Brazos',
    lunge:         'Zancada',
    arm_raise:     'Elevación de Brazos',
    joint_mobility:'Movilidad Articular',
  };

  const SEGMENT_MAP = {
    neck:  ['LEFT_EAR','RIGHT_EAR','LEFT_SHOULDER','RIGHT_SHOULDER','NOSE'],
    trunk: ['LEFT_SHOULDER','RIGHT_SHOULDER','LEFT_HIP','RIGHT_HIP'],
    hip:   ['LEFT_HIP','RIGHT_HIP','LEFT_KNEE','RIGHT_KNEE'],
    arms:  ['LEFT_SHOULDER','RIGHT_SHOULDER','LEFT_ELBOW','RIGHT_ELBOW','LEFT_WRIST','RIGHT_WRIST'],
    legs:  ['LEFT_HIP','RIGHT_HIP','LEFT_KNEE','RIGHT_KNEE','LEFT_ANKLE','RIGHT_ANKLE'],
  };

  // ── Helpers matemáticos ──────────────────────────────────────────────────
  function vec2(a, b) { return { x: b.x - a.x, y: b.y - a.y }; }
  function dot2(u, v) { return u.x * v.x + u.y * v.y; }
  function mag2(v)    { return Math.sqrt(v.x * v.x + v.y * v.y); }
  function angleBetween(a, vertex, b) {
    const u = vec2(vertex, a);
    const v = vec2(vertex, b);
    const cosA = dot2(u, v) / (mag2(u) * mag2(v) + 1e-9);
    return Math.acos(Math.max(-1, Math.min(1, cosA))) * (180 / Math.PI);
  }
  function kp(keypoints, name) {
    const p = keypoints[name];
    if (!p || (p.visibility ?? 1) < 0.25) return null;
    return p;
  }

  // ── EMA suavizado temporal ────────────────────────────────────────────────
  function applyEMA(newKps) {
    if (!biomechEmaKps) { biomechEmaKps = { ...newKps }; return { ...newKps }; }
    const result = {};
    Object.keys(newKps).forEach(name => {
      const n = newKps[name];
      const e = biomechEmaKps[name] || n;
      result[name] = {
        x: e.x + EMA_ALPHA * (n.x - e.x),
        y: e.y + EMA_ALPHA * (n.y - e.y),
        z: (e.z || 0) + EMA_ALPHA * ((n.z || 0) - (e.z || 0)),
        visibility: n.visibility,
      };
    });
    biomechEmaKps = result;
    return result;
  }

  // ── Dibujo de esqueleto biomecánico (estilo imagen referencia) ───────────
  function drawBiomechPose(keypoints) {
    const video = $('#camera-video');
    const overlay = $('#posture-canvas');
    if (!overlay || !video || !video.clientWidth) return;
    const rect = overlay.getBoundingClientRect();
    if (!rect.width) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const pw = Math.round(rect.width * dpr);
    const ph = Math.round(rect.height * dpr);
    if (overlay.width !== pw || overlay.height !== ph) {
      overlay.width = pw;
      overlay.height = ph;
    }
    const ctx = overlay.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, rect.width, rect.height);

    const sw = video.videoWidth || video.clientWidth;
    const sh = video.videoHeight || video.clientHeight;
    if (!sw || !sh) return;
    const scale = Math.max(rect.width / sw, rect.height / sh);
    const ox = (rect.width  - sw * scale) / 2;
    const oy = (rect.height - sh * scale) / 2;

    const pt = name => {
      const p = kp(keypoints, name);
      if (!p) return null;
      return { x: ox + p.x * sw * scale, y: oy + p.y * sh * scale };
    };

    // Determinar puntos con riesgo
    const riskSet = computeRiskSet(keypoints);

    const lineW = Math.max(2.5, rect.width / 190);
    const shadowR = isMobileCameraDevice() ? 0 : 7;

    // 1. Conexiones del esqueleto
    poseConnections.forEach(([sName, eName]) => {
      const a = pt(sName), b = pt(eName);
      if (!a || !b) return;
      const isRisk = riskSet.has(sName) || riskSet.has(eName);
      ctx.save();
      // Contorno oscuro
      ctx.lineWidth = lineW + 3;
      ctx.lineCap = 'round';
      ctx.strokeStyle = 'rgba(0,0,0,0.55)';
      ctx.shadowBlur = 0;
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
      // Línea coloreada
      ctx.lineWidth = lineW;
      ctx.strokeStyle = isRisk ? '#ef4444' : '#f59e0b';
      ctx.shadowColor  = ctx.strokeStyle;
      ctx.shadowBlur   = shadowR;
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
      ctx.restore();
    });

    // 2. Bracing diagonal de tronco (como la imagen de referencia)
    const ls = pt('LEFT_SHOULDER'), rs = pt('RIGHT_SHOULDER');
    const lh = pt('LEFT_HIP'),      rh = pt('RIGHT_HIP');
    if (ls && rs && lh && rh) {
      ctx.save();
      ctx.lineWidth = lineW * 0.7;
      ctx.strokeStyle = 'rgba(251,191,36,0.55)';
      ctx.setLineDash([5, 7]);
      ctx.shadowBlur = 0;
      ctx.beginPath(); ctx.moveTo(ls.x, ls.y); ctx.lineTo(rh.x, rh.y); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(rs.x, rs.y); ctx.lineTo(lh.x, lh.y); ctx.stroke();
      ctx.setLineDash([]);
      ctx.restore();
    }

    // 3. Nodos articulares
    const headPt = pt('NOSE') || pt('LEFT_EAR') || pt('RIGHT_EAR');
    Object.keys(keypoints).forEach(name => {
      const p = pt(name);
      if (!p) return;
      const isHead = ['NOSE','LEFT_EYE','RIGHT_EYE','LEFT_EAR','RIGHT_EAR',
                      'LEFT_EYE_INNER','LEFT_EYE_OUTER','RIGHT_EYE_INNER','RIGHT_EYE_OUTER',
                      'MOUTH_LEFT','MOUTH_RIGHT'].includes(name);
      if (isHead) return; // la cabeza se dibuja aparte
      const isRisk = riskSet.has(name);
      const r = Math.max(5, rect.width / 100);
      ctx.save();
      ctx.shadowColor = isRisk ? '#ef4444' : '#f59e0b';
      ctx.shadowBlur  = shadowR + 2;
      ctx.beginPath();
      ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
      ctx.fillStyle = isRisk ? '#ef4444' : '#f59e0b';
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.beginPath();
      ctx.arc(p.x, p.y, r * 0.38, 0, Math.PI * 2);
      ctx.fillStyle = '#fff';
      ctx.fill();
      ctx.restore();
    });

    // 4. Disco cabeza (estilo imagen: círculo ámbar grande)
    if (headPt) {
      const r = Math.max(14, rect.width / 42);
      ctx.save();
      ctx.shadowColor = '#f59e0b';
      ctx.shadowBlur  = isMobileCameraDevice() ? 0 : 14;
      ctx.beginPath();
      ctx.arc(headPt.x, headPt.y, r, 0, Math.PI * 2);
      ctx.fillStyle = '#f59e0b';
      ctx.fill();
      ctx.strokeStyle = '#fef3c7';
      ctx.lineWidth = 2.5;
      ctx.stroke();
      ctx.restore();
    }

    // 5. Badges de ángulos clave
    if (biomechSession?.lastAngleSnapshot) {
      const snap = biomechSession.lastAngleSnapshot;
      const badgePairs = [
        ['knee_left',  'LEFT_KNEE'],
        ['knee_right', 'RIGHT_KNEE'],
        ['trunk',      'LEFT_SHOULDER'],
        ['hip_left',   'LEFT_HIP'],
      ];
      badgePairs.forEach(([key, landmark]) => {
        const p = pt(landmark);
        const val = snap[key];
        if (!p || val == null) return;
        const isRisk = riskSet.has(landmark);
        const bx = p.x + 12, by = p.y - 10;
        const label = `${Math.round(val)}°`;
        ctx.save();
        ctx.font = `bold ${Math.max(10, rect.width / 55)}px system-ui`;
        const tw = ctx.measureText(label).width;
        ctx.fillStyle = isRisk ? 'rgba(239,68,68,0.9)' : 'rgba(15,23,42,0.75)';
        const pad = 3;
        ctx.beginPath();
        ctx.roundRect(bx - pad, by - 13, tw + pad * 2, 17, 4);
        ctx.fill();
        ctx.fillStyle = isRisk ? '#fff' : '#f8fafc';
        ctx.fillText(label, bx, by);
        ctx.restore();
      });
    }
  }

  // ── Calcular qué landmarks tienen riesgo según los eventos actuales ───────
  function computeRiskSet(keypoints) {
    const set = new Set();
    if (!biomechSession) return set;
    const riskJointMap = {
      knee_left:    ['LEFT_KNEE','LEFT_HIP','LEFT_ANKLE'],
      knee_right:   ['RIGHT_KNEE','RIGHT_HIP','RIGHT_ANKLE'],
      shoulder_left:['LEFT_SHOULDER','LEFT_ELBOW'],
      shoulder_right:['RIGHT_SHOULDER','RIGHT_ELBOW'],
      hip_left:     ['LEFT_HIP','LEFT_SHOULDER'],
      hip_right:    ['RIGHT_HIP','RIGHT_SHOULDER'],
      trunk:        ['LEFT_SHOULDER','RIGHT_SHOULDER','LEFT_HIP','RIGHT_HIP'],
      elbow_left:   ['LEFT_ELBOW','LEFT_WRIST','LEFT_SHOULDER'],
      elbow_right:  ['RIGHT_ELBOW','RIGHT_WRIST','RIGHT_SHOULDER'],
    };
    const recentCutoff = Date.now() - 2500;
    biomechSession.rawEvents
      .filter(ev => ev.ts >= recentCutoff)
      .forEach(ev => {
        const lms = riskJointMap[ev.joint] || [];
        lms.forEach(l => set.add(l));
      });
    return set;
  }

  // ── Análisis biomecánico por fotograma ────────────────────────────────────
  function analyzeBiomechFrame(keypoints) {
    if (!biomechSession?.isRunning || biomechSession.isPaused) return;
    const ex = biomechSession.exerciseKey;
    const snap = {};
    const errors = [];

    const lsh = kp(keypoints,'LEFT_SHOULDER'),  rsh = kp(keypoints,'RIGHT_SHOULDER');
    const lhi = kp(keypoints,'LEFT_HIP'),        rhi = kp(keypoints,'RIGHT_HIP');
    const lkn = kp(keypoints,'LEFT_KNEE'),       rkn = kp(keypoints,'RIGHT_KNEE');
    const lan = kp(keypoints,'LEFT_ANKLE'),      ran = kp(keypoints,'RIGHT_ANKLE');
    const lel = kp(keypoints,'LEFT_ELBOW'),      rel = kp(keypoints,'RIGHT_ELBOW');
    const lwr = kp(keypoints,'LEFT_WRIST'),      rwr = kp(keypoints,'RIGHT_WRIST');

    // Ángulo rodilla izquierda
    if (lhi && lkn && lan) {
      snap.knee_left = angleBetween(lhi, lkn, lan);
    }
    // Ángulo rodilla derecha
    if (rhi && rkn && ran) {
      snap.knee_right = angleBetween(rhi, rkn, ran);
    }
    // Ángulo cadera izquierda (tronco-muslo)
    if (lsh && lhi && lkn) {
      snap.hip_left = angleBetween(lsh, lhi, lkn);
    }
    if (rsh && rhi && rkn) {
      snap.hip_right = angleBetween(rsh, rhi, rkn);
    }
    // Inclinación lateral del tronco
    if (lsh && rsh && lhi && rhi) {
      const midSh = { x:(lsh.x+rsh.x)/2, y:(lsh.y+rsh.y)/2 };
      const midHi = { x:(lhi.x+rhi.x)/2, y:(lhi.y+rhi.y)/2 };
      const dx = midSh.x - midHi.x;
      const dy = midSh.y - midHi.y;
      snap.trunk = Math.abs(Math.atan2(dx, Math.abs(dy)) * 180 / Math.PI);
    }
    // Ángulo codo izquierdo
    if (lsh && lel && lwr) snap.elbow_left = angleBetween(lsh, lel, lwr);
    if (rsh && rel && rwr) snap.elbow_right = angleBetween(rsh, rel, rwr);

    // Asimetría de hombros
    if (lsh && rsh) {
      snap.shoulder_tilt = Math.abs((lsh.y - rsh.y) * 100);
    }
    // Asimetría de cadera
    if (lhi && rhi) {
      snap.hip_tilt = Math.abs((lhi.y - rhi.y) * 100);
    }

    biomechSession.lastAngleSnapshot = snap;

    // ── Reglas por ejercicio ─────────────────────────────────────────────
    if (ex === 'squat') {
      // Profundidad: en la fase baja, el ángulo de rodilla debería bajar de squatDepth
      const kL = snap.knee_left, kR = snap.knee_right;
      if (kL != null && kL < biomechThresholds.squatDepth) {
        errors.push({ name:'Profundidad insuficiente (izq)', joint:'knee_left', angle:kL, ref:biomechThresholds.squatDepth, severity:'medium' });
      }
      if (kR != null && kR < biomechThresholds.squatDepth) {
        errors.push({ name:'Profundidad insuficiente (der)', joint:'knee_right', angle:kR, ref:biomechThresholds.squatDepth, severity:'medium' });
      }
      // Inclinación de tronco
      if (snap.trunk != null && snap.trunk > biomechThresholds.trunk) {
        errors.push({ name:'Inclinación excesiva del tronco', joint:'trunk', angle:snap.trunk, ref:biomechThresholds.trunk, severity:'high' });
      }
      // Valgus: si la rodilla cae hacia adentro respecto a la cadera
      if (lhi && lkn && lan && rhi && rkn && ran) {
        const leftValgus  = Math.abs((lkn.x - lhi.x) * 100);
        const rightValgus = Math.abs((rkn.x - rhi.x) * 100);
        if (leftValgus > biomechThresholds.valgus) {
          errors.push({ name:'Valgo de rodilla izquierda', joint:'knee_left', angle:leftValgus, ref:biomechThresholds.valgus, severity:'high' });
        }
        if (rightValgus > biomechThresholds.valgus) {
          errors.push({ name:'Valgo de rodilla derecha', joint:'knee_right', angle:rightValgus, ref:biomechThresholds.valgus, severity:'high' });
        }
      }
    }

    if (ex === 'push_up') {
      const eL = snap.elbow_left, eR = snap.elbow_right;
      if (eL != null && eL > biomechThresholds.pushupElbow) {
        errors.push({ name:'Rango codo izq insuficiente', joint:'elbow_left', angle:eL, ref:biomechThresholds.pushupElbow, severity:'medium' });
      }
      if (eR != null && eR > biomechThresholds.pushupElbow) {
        errors.push({ name:'Rango codo der insuficiente', joint:'elbow_right', angle:eR, ref:biomechThresholds.pushupElbow, severity:'medium' });
      }
      if (snap.trunk != null && snap.trunk > 15) {
        errors.push({ name:'Cadera caída / columna desalineada', joint:'trunk', angle:snap.trunk, ref:15, severity:'high' });
      }
    }

    if (ex === 'lunge') {
      if (snap.knee_left != null && snap.knee_left < 85) {
        errors.push({ name:'Rodilla adelantada (izq)', joint:'knee_left', angle:snap.knee_left, ref:85, severity:'medium' });
      }
      if (snap.knee_right != null && snap.knee_right < 85) {
        errors.push({ name:'Rodilla adelantada (der)', joint:'knee_right', angle:snap.knee_right, ref:85, severity:'medium' });
      }
      if (snap.trunk != null && snap.trunk > 20) {
        errors.push({ name:'Tronco inclinado en zancada', joint:'trunk', angle:snap.trunk, ref:20, severity:'medium' });
      }
    }

    if (ex === 'arm_raise') {
      const eL = snap.elbow_left, eR = snap.elbow_right;
      if (eL != null && eL < 150) {
        errors.push({ name:'Rango elevación brazo izq', joint:'elbow_left', angle:eL, ref:150, severity:'low' });
      }
      if (eR != null && eR < 150) {
        errors.push({ name:'Rango elevación brazo der', joint:'elbow_right', angle:eR, ref:150, severity:'low' });
      }
      if (snap.shoulder_tilt != null && snap.shoulder_tilt > biomechThresholds.asymmetry) {
        errors.push({ name:'Asimetría de hombros', joint:'shoulder_left', angle:snap.shoulder_tilt, ref:biomechThresholds.asymmetry, severity:'medium' });
      }
    }

    if (ex === 'joint_mobility') {
      if (snap.trunk != null && snap.trunk > 10) {
        errors.push({ name:'Desvío lateral de tronco', joint:'trunk', angle:snap.trunk, ref:10, severity:'low' });
      }
      if (snap.hip_tilt != null && snap.hip_tilt > biomechThresholds.asymmetry) {
        errors.push({ name:'Asimetría pélvica', joint:'hip_left', angle:snap.hip_tilt, ref:biomechThresholds.asymmetry, severity:'medium' });
      }
    }

    // Asimetría bilateral general
    if (snap.knee_left != null && snap.knee_right != null) {
      const diff = Math.abs(snap.knee_left - snap.knee_right);
      if (diff > 15) {
        errors.push({ name:'Asimetría rodillas', joint:'knee_left', angle:diff, ref:15, severity:'medium' });
      }
    }

    // ── Acumular errores con debounce ─────────────────────────────────────
    const now = Date.now();
    const tsSeconds = (now - biomechSession.startedAt - biomechSession.pausedTotalMs) / 1000;
    errors.forEach(err => {
      // Buscar si ya existe un evento con este nombre
      let existing = biomechSession.events.find(e => e.name === err.name);
      if (!existing) {
        existing = { ...err, frequency: 0, confirmFrames: 0, lastTs: 0, firstTs: tsSeconds };
        biomechSession.events.push(existing);
      }
      existing.confirmFrames = (existing.confirmFrames || 0) + 1;
      if (existing.confirmFrames >= biomechThresholds.framesDebounce) {
        existing.frequency += 1;
        existing.lastTs = tsSeconds;
        existing.angle = err.angle; // actualizar ángulo
        // Agregar al cronológico solo si han pasado ≥ 2 s desde la última
        if (tsSeconds - (existing.lastChrono || -99) >= 2) {
          biomechSession.rawEvents.push({ ...err, ts: now, tsSeconds });
          existing.lastChrono = tsSeconds;
        }
        existing.confirmFrames = 0;
      }
    });
    // Resetear confirmFrames de los que no aparecen en este frame
    biomechSession.events.forEach(ev => {
      if (!errors.find(e => e.name === ev.name)) {
        ev.confirmFrames = Math.max(0, (ev.confirmFrames || 0) - 1);
      }
    });

    // ── Actualizar HUD ───────────────────────────────────────────────────
    updateBiomechHUD(keypoints, snap);
  }

  // ── Actualizar HUD en tiempo real ─────────────────────────────────────────
  function updateBiomechHUD(keypoints, snap) {
    if (!biomechSession) return;
    // Contador de errores
    const totalErrors = biomechSession.events.filter(e => e.frequency > 0).length;
    const errorEl = $('#hud-error-counter');
    if (errorEl) errorEl.textContent = `${totalErrors} Error${totalErrors !== 1 ? 'es' : ''}`;

    // Calidad de seguimiento
    const visible = Object.values(keypoints).filter(p => (p?.visibility ?? 1) > 0.5).length;
    const total   = Object.keys(keypoints).length || 1;
    const quality = Math.round(visible / total * 100);
    const trackEl  = $('#hud-tracking-status');
    const trackDot = $('#hud-tracking-dot');
    if (trackEl) trackEl.textContent = quality > 75 ? 'Detección Óptima' : quality > 50 ? 'Detección Parcial' : 'Detección Débil';
    if (trackDot) trackDot.style.background = quality > 75 ? '#10b981' : quality > 50 ? '#f59e0b' : '#ef4444';

    // FPS
    const now = performance.now();
    biomechFpsCounter.frames++;
    if (now - biomechFpsCounter.lastTs >= 1000) {
      biomechFpsCounter.fps = biomechFpsCounter.frames;
      biomechFpsCounter.frames = 0;
      biomechFpsCounter.lastTs = now;
      const fpsEl = $('#hud-fps-text');
      if (fpsEl) fpsEl.textContent = `${biomechFpsCounter.fps} FPS · Suavizado`;
    }

    // Segmentos laterales
    const segSnap = {
      neck: snap.shoulder_tilt != null ? { status: snap.shoulder_tilt > 8 ? '⚠ Asimétrico' : 'Alineada', angle: `${snap.shoulder_tilt?.toFixed(1) ?? '—'}%`, risk: snap.shoulder_tilt > 8 } : null,
      trunk: snap.trunk != null       ? { status: snap.trunk > biomechThresholds.trunk ? '⚠ Inclinado' : 'Neutro',   angle: `${snap.trunk.toFixed(1)}°`, risk: snap.trunk > biomechThresholds.trunk } : null,
      hip:  snap.hip_tilt != null     ? { status: snap.hip_tilt > biomechThresholds.asymmetry ? '⚠ Basculación' : 'Simétrica', angle: `${snap.hip_tilt.toFixed(1)}%`, risk: snap.hip_tilt > biomechThresholds.asymmetry } : null,
      arms: snap.elbow_left != null   ? { status: snap.elbow_left < 100 ? '⚠ Rango limitado' : 'En rango', angle: `${snap.elbow_left.toFixed(0)}°`, risk: snap.elbow_left < 100 } : null,
      legs: snap.knee_left != null    ? { status: snap.knee_left < 100 ? '⚠ Flexión baja' : 'Alineadas', angle: `${snap.knee_left.toFixed(0)}°`, risk: snap.knee_left < 100 } : null,
    };
    Object.entries(segSnap).forEach(([seg, data]) => {
      if (!data) return;
      const statusEl = $(`#seg-${seg}-status`);
      const angleEl  = $(`#seg-${seg}-angle`);
      const itemEl   = $(`#seg-${seg}`);
      if (statusEl) { statusEl.textContent = data.status; statusEl.style.color = data.risk ? '#ef4444' : '#10b981'; }
      if (angleEl)  angleEl.textContent = data.angle;
      if (itemEl)   itemEl.style.borderLeftColor = data.risk ? '#ef4444' : '#10b981';
    });

    // Prompt en la parte inferior
    const promptEl = $('#biomech-bottom-prompt');
    if (promptEl) {
      const riskEvents = biomechSession.events.filter(e => e.frequency > 0 && e.confirmFrames >= 0);
      if (riskEvents.length > 0) {
        const top = riskEvents.sort((a, b) => b.frequency - a.frequency)[0];
        promptEl.textContent = `⚠ ${top.name} detectado (${top.frequency}×) · ${top.joint ? jointLabels[top.joint] || top.joint : ''}`;
        promptEl.style.background = 'rgba(239,68,68,0.9)';
      } else {
        promptEl.textContent = '✓ Postura correcta · Continúa el movimiento';
        promptEl.style.background = 'rgba(16,185,129,0.85)';
      }
    }

    // Calidad de seguimiento (goodFrames)
    if (quality > 60) biomechSession.goodFrames++;
    biomechSession.frameCount++;
  }

  // ── Cronómetro ───────────────────────────────────────────────────────────
  function formatStopwatch(ms) {
    const totalS = Math.floor(ms / 1000);
    const m = String(Math.floor(totalS / 60)).padStart(2, '0');
    const s = String(totalS % 60).padStart(2, '0');
    return `${m}:${s}`;
  }

  function startStopwatch() {
    if (biomechStopwatchTimer) return;
    biomechStopwatchTimer = setInterval(() => {
      if (!biomechSession || biomechSession.isPaused) return;
      const elapsed = Date.now() - biomechSession.startedAt - biomechSession.pausedTotalMs;
      const el = $('#hud-stopwatch');
      if (el) el.textContent = formatStopwatch(elapsed);
    }, 500);
  }

  function stopStopwatch() {
    if (biomechStopwatchTimer) { clearInterval(biomechStopwatchTimer); biomechStopwatchTimer = null; }
  }

  // ── Loop de captura y análisis en tiempo real ─────────────────────────────
  function biomechLoop() {
    if (!biomechSession?.isRunning || !cameraStream) {
      biomechRequestFrame = null;
      return;
    }
    const now = performance.now();
    if (!biomechSession.isPaused && now - biomechLastCapture >= BIOMECH_CAPTURE_MS) {
      biomechLastCapture = now;
      captureBiomechFrame().then(kpsData => {
        if (!kpsData || !biomechSession?.isRunning) return;
        const smoothed = applyEMA(kpsData);
        biomechCurrentKps = smoothed;
        drawBiomechPose(smoothed);
        analyzeBiomechFrame(smoothed);
      }).catch(() => {});
    }
    biomechRequestFrame = requestAnimationFrame(biomechLoop);
  }

  async function captureBiomechFrame() {
    const video = $('#camera-video');
    if (!video || !video.videoWidth) return null;
    if (!biomechVideoCanvas) biomechVideoCanvas = document.createElement('canvas');
    const scale = Math.min(1, 480 / video.videoWidth);
    biomechVideoCanvas.width  = Math.round(video.videoWidth  * scale);
    biomechVideoCanvas.height = Math.round(video.videoHeight * scale);
    biomechVideoCanvas.getContext('2d').drawImage(video, 0, 0, biomechVideoCanvas.width, biomechVideoCanvas.height);
    return new Promise(resolve => {
      biomechVideoCanvas.toBlob(async blob => {
        if (!blob) return resolve(null);
        const file = new File([blob], `bm-${Date.now()}.jpg`, { type: 'image/jpeg' });
        try {
          const exerciseType = biomechSession?.exerciseKey || 'squat';
          const viewType     = $('#assessment-view-type')?.value || 'front';
          const result = await api.analyzePosePreview(file, exerciseType, viewType);
          if (result?.success && result.keypoints_data) resolve(result.keypoints_data);
          else resolve(null);
        } catch { resolve(null); }
      }, 'image/jpeg', 0.60);
    });
  }

  // ── Controles de evaluación ───────────────────────────────────────────────
  async function startBiomechEval() {
    const athleteId = $('#assessment-athlete')?.value;
    if (!athleteId) {
      showToast('Selecciona un atleta antes de iniciar la evaluación biomecánica.', 'warning');
      return;
    }
    const exerciseSelect = $('#biomech-exercise-select') || $('#assessment-exercise');
    const exerciseKey    = exerciseSelect?.value || 'squat';
    const athlete        = athletes.find(a => String(a.id) === String(athleteId));
    const athleteName    = athlete?.full_name || `Atleta #${athleteId}`;

    // Iniciar cámara si no está activa
    if (!cameraStream) {
      const ok = await startCamera();
      if (!ok) return;
      await new Promise(r => setTimeout(r, 600)); // esperar que el video arranque
    }

    biomechEmaKps = null;
    biomechCurrentKps = null;
    biomechFpsCounter = { frames: 0, lastTs: 0, fps: 0 };

    biomechSession = {
      athleteId,
      athleteName,
      exerciseKey,
      exerciseLabel: EXERCISE_LABELS[exerciseKey] || exerciseKey,
      startedAt: Date.now(),
      pausedAt: null,
      pausedTotalMs: 0,
      isRunning: true,
      isPaused: false,
      events: [],
      rawEvents: [],
      frameCount: 0,
      goodFrames: 0,
      lastAngleSnapshot: {},
      savedAssessmentId: null,
    };

    // Mostrar HUD
    const hudTop   = $('#biomech-hud-top');
    const hudRight = $('#biomech-hud-right');
    const prompt   = $('#biomech-bottom-prompt');
    if (hudTop)   hudTop.style.display   = 'flex';
    if (hudRight) hudRight.style.display = 'block';
    if (prompt)   prompt.style.display   = 'block';

    // Llenar HUD con datos iniciales
    const hudAthlete  = $('#hud-athlete-name');
    const hudExercise = $('#hud-exercise-name');
    if (hudAthlete)  hudAthlete.textContent  = athleteName;
    if (hudExercise) hudExercise.textContent = biomechSession.exerciseLabel;
    const recDot = $('#hud-rec-dot');
    if (recDot) recDot.style.background = '#ef4444';

    // Botones
    setBiomechControlState('running');
    startStopwatch();
    biomechLoop();
    showToast(`Evaluación iniciada: ${biomechSession.exerciseLabel}. Realiza el movimiento.`, 'info');
  }

  function pauseBiomechEval() {
    if (!biomechSession?.isRunning || biomechSession.isPaused) return;
    biomechSession.isPaused = true;
    biomechSession.pausedAt = Date.now();
    setBiomechControlState('paused');
    const recDot = $('#hud-rec-dot');
    if (recDot) recDot.style.background = '#f59e0b';
    showToast('Evaluación pausada.', 'info');
  }

  function resumeBiomechEval() {
    if (!biomechSession?.isRunning || !biomechSession.isPaused) return;
    biomechSession.pausedTotalMs += Date.now() - (biomechSession.pausedAt || Date.now());
    biomechSession.pausedAt = null;
    biomechSession.isPaused = false;
    setBiomechControlState('running');
    const recDot = $('#hud-rec-dot');
    if (recDot) recDot.style.background = '#ef4444';
    showToast('Evaluación reanudada.', 'info');
  }

  async function finishBiomechEval() {
    if (!biomechSession) return;
    const session = biomechSession;
    biomechSession = null;
    session.isRunning = false;
    stopStopwatch();
    if (biomechRequestFrame) { cancelAnimationFrame(biomechRequestFrame); biomechRequestFrame = null; }

    // Ocultar HUD
    ['#biomech-hud-top','#biomech-hud-right','#biomech-bottom-prompt'].forEach(sel => {
      const el = $(sel); if (el) el.style.display = 'none';
    });
    setBiomechControlState('idle');

    const durationMs = Date.now() - session.startedAt - session.pausedTotalMs;
    const durationSec = Math.round(durationMs / 1000);
    const qualityPct  = session.frameCount > 0 ? Math.round(session.goodFrames / session.frameCount * 100) : 0;
    const confirmedEvents = session.events.filter(e => e.frequency > 0);
    const totalFrequency = confirmedEvents.reduce((total, event) => total + event.frequency, 0);
    const riskScore = Math.min(100, Math.round(
      totalFrequency * 4 + confirmedEvents.filter(event => event.severity === 'high').length * 12
    ));
    const riskLevel = riskScore < 25 ? 'low' : riskScore < 55 ? 'medium' : riskScore < 80 ? 'high' : 'critical';
    const jointAngles = {};
    const jointKeys = {
      knee_left: 'knee_left',
      knee_right: 'knee_right',
      hip_left: 'hip_left',
      hip_right: 'hip_right',
      elbow_left: 'elbow_left',
      elbow_right: 'elbow_right',
      trunk: 'spine_lateral',
    };
    Object.entries(jointKeys).forEach(([snapshotKey, jointKey]) => {
      const angle = session.lastAngleSnapshot?.[snapshotKey];
      if (Number.isFinite(angle)) jointAngles[jointKey] = Number(angle.toFixed(2));
    });
    const detectedIssues = confirmedEvents.map(event => ({
      zone: event.joint || 'Movimiento',
      description: `${event.name} (${event.frequency} veces)`,
      severity: event.severity || 'medium',
      type: 'biomechanical',
    }));

    // Guardar en backend
    let savedId = null;
    try {
      const payload = {
        athlete_id:            session.athleteId,
        exercise_type:         session.exerciseKey,
        view_type:             $('#assessment-view-type')?.value || 'frontal',
        duration_seconds:      durationSec,
        tracking_quality:      qualityPct,
        risk_score:            riskScore,
        risk_level:            riskLevel,
        joint_angles:          jointAngles,
        detected_issues:       detectedIssues,
        recommendations:       [],
        exercise_thresholds:   { ...biomechThresholds },
        exercise_feedback:     {
          exercise_display: session.exerciseLabel,
          status: confirmedEvents.length ? 'warning' : 'success',
          summary: confirmedEvents.length
            ? `Se detectaron ${confirmedEvents.length} patrones biomecánicos durante la sesión.`
            : 'No se registraron desviaciones confirmadas durante la sesión.',
          cues: confirmedEvents.map(event => event.name),
          session_statistics: {
            frames_analyzed: session.frameCount,
            duration_seconds: durationSec,
            tracking_quality: qualityPct,
            repeated_findings: totalFrequency,
            total_events: confirmedEvents.length,
            risk_score: riskScore,
          },
        },
        biomechanical_events:  confirmedEvents.map(ev => ({
          error_name:      ev.name,
          exercise_type:   session.exerciseKey,
          timestamp_seconds: ev.firstTs ?? 0,
          joint:           ev.joint || '',
          angle_degrees:   ev.angle != null ? parseFloat(ev.angle.toFixed(2)) : null,
          reference_range: `${ev.ref ?? ''}`,
          frequency:       ev.frequency,
          confidence:      Math.round(Math.min(1, ev.frequency / 5) * 100),
          severity:        ev.severity || 'medium',
          observations:    `${ev.name}; frecuencia: ${ev.frequency}${ev.angle != null ? `; ángulo observado: ${ev.angle.toFixed(1)}°` : ''}${ev.ref != null ? `; referencia del umbral: ${ev.ref}` : ''}.`,
        })),
      };
      const resp = await api.saveBiomechanicalSession(payload);
      savedId = resp?.id || resp?.assessment?.id || null;
      if (savedId) showToast('Estadísticas y observaciones de la evaluación guardadas.', 'success');
    } catch (err) {
      showToast(`No se pudo guardar en el servidor: ${err.message}`, 'warning');
    }

    // Abrir modal de informe
    openBiomechReport(session, durationSec, qualityPct, confirmedEvents, savedId);
  }

  function setBiomechControlState(state) {
    // state: 'idle' | 'running' | 'paused'
    const start   = $('#btn-eval-start');
    const pause   = $('#btn-eval-pause');
    const resume  = $('#btn-eval-resume');
    const finish  = $('#btn-eval-finish');
    if (!start) return;
    if (state === 'idle') {
      start.style.display   = '';
      pause.style.display   = 'none';
      resume.style.display  = 'none';
      finish.style.display  = 'none';
    } else if (state === 'running') {
      start.style.display   = 'none';
      pause.style.display   = '';
      resume.style.display  = 'none';
      finish.style.display  = '';
    } else if (state === 'paused') {
      start.style.display   = 'none';
      pause.style.display   = 'none';
      resume.style.display  = '';
      finish.style.display  = '';
    }
  }

  // ── Modal de informe ──────────────────────────────────────────────────────
  function openBiomechReport(session, durationSec, qualityPct, events, savedId) {
    const modal = $('#biomech-report-modal');
    if (!modal) return;
    modal.style.display = 'flex';
    modal._savedId = savedId;
    modal._session = session;

    // ── Sección A: Resumen ────────────────────────────────────────────────
    const now = new Date();
    $('#rep-athlete-name').textContent   = session.athleteName;
    const athlete = athletes.find(a => String(a.id) === String(session.athleteId));
    $('#rep-athlete-sport').textContent  = `Deporte: ${athlete?.sport || '—'}`;
    $('#rep-session-date').textContent   = `Fecha: ${now.toLocaleDateString('es-EC')} ${now.toLocaleTimeString('es-EC', {hour:'2-digit',minute:'2-digit'})}`;
    $('#rep-exercise-display').textContent = session.exerciseLabel;
    $('#rep-duration').textContent       = `Duración: ${formatStopwatch(durationSec * 1000)}`;
    $('#rep-tracking-quality').textContent = `Calidad de seguimiento: ${qualityPct}%`;
    // Riesgo estimado
    const totalFreq = events.reduce((s, e) => s + e.frequency, 0);
    const riskScore = Math.min(100, Math.round(totalFreq * 4 + events.filter(e => e.severity === 'high').length * 12));
    const riskLevel = riskScore < 25 ? 'Bajo' : riskScore < 55 ? 'Medio' : riskScore < 80 ? 'Alto' : 'Crítico';
    const riskClass = riskScore < 25 ? 'badge-blue' : riskScore < 55 ? 'badge-yellow' : riskScore < 80 ? 'badge-red' : 'risk-critical';
    $('#rep-risk-score').textContent = riskScore;
    const badge = $('#rep-risk-badge');
    if (badge) { badge.textContent = riskLevel; badge.className = `badge ${riskClass}`; }
    $('#rep-confidence').textContent = `Confianza: ${qualityPct}%`;

    // ── Sección B: Tabla de errores ───────────────────────────────────────
    const tbody = $('#report-errors-tbody');
    if (tbody) {
      tbody.innerHTML = events.length
        ? events.map(ev => {
            const sevColor = ev.severity === 'high' ? '#ef4444' : ev.severity === 'medium' ? '#f59e0b' : '#3b82f6';
            return `<tr>
              <td><strong>${escapeHtml(ev.name)}</strong></td>
              <td>${escapeHtml(session.exerciseLabel)}</td>
              <td>${escapeHtml(jointLabels[ev.joint] || ev.joint || '—')}</td>
              <td>${ev.angle != null ? escapeHtml(ev.angle.toFixed(1)) + '°' : '—'}</td>
              <td>${escapeHtml(String(ev.ref ?? '—'))}</td>
              <td>${ev.frequency}</td>
              <td>${Math.round(Math.min(1, ev.frequency / 5) * 100)}%</td>
              <td><span style="color:${sevColor};font-weight:600">${escapeHtml(ev.severity || 'medium')}</span></td>
            </tr>`;
          }).join('')
        : `<tr><td colspan="8" class="text-center text-sm text-gray py-3">Sin errores biomecánicos detectados en esta sesión.</td></tr>`;
    }

    // ── Sección C: Esqueleto en canvas ────────────────────────────────────
    drawReportMannequin(events);

    // ── Sección D: Timeline cronológico ──────────────────────────────────
    const timelineEl = $('#report-events-timeline');
    if (timelineEl) {
      const chrono = session.rawEvents.slice().sort((a, b) => a.tsSeconds - b.tsSeconds);
      timelineEl.innerHTML = chrono.length
        ? chrono.map(ev => {
            const m = String(Math.floor(ev.tsSeconds / 60)).padStart(2,'0');
            const s = String(Math.floor(ev.tsSeconds % 60)).padStart(2,'0');
            return `<div class="biomech-timeline-item">
              <span style="font-size:.7rem;color:#94a3b8;min-width:48px">${m}:${s}</span>
              <span style="flex:1">${escapeHtml(ev.name)}</span>
              <span style="font-size:.7rem;color:${ev.severity==='high'?'#ef4444':'#f59e0b'}">${escapeHtml(ev.severity || 'medium')}</span>
            </div>`;
          }).join('')
        : '<div class="text-sm text-gray py-2">Sin eventos de desviación registrados.</div>';
    }

    // Limpiar campos médico
    const doctorNotes = $('#rep-doctor-notes');
    if (doctorNotes) doctorNotes.value = '';
    ['technical','mobility','strength','stability','flexibility','followup'].forEach(k => {
      const el = $(`#rec-${k}`); if (el) el.value = '';
    });
    const approved = $('#rep-doctor-approved');
    if (approved) approved.checked = false;
    const approvalStatus = $('#rep-approval-status');
    if (approvalStatus) approvalStatus.textContent = 'Pendiente de aprobación. Al marcar, se registra tu firma digital y fecha de revisión.';
  }

  // ── Mannequin (Sección C) ─────────────────────────────────────────────────
  function drawReportMannequin(events) {
    const canvas = $('#report-mannequin-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);

    // Fondo
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, W, H);

    // Figura humana estilizada (proporciones relativas)
    const cx = W / 2;
    const joints = {
      head:     { x: cx,       y: H * 0.09 },
      neck:     { x: cx,       y: H * 0.17 },
      lsh:      { x: cx - W*0.14, y: H * 0.23 },
      rsh:      { x: cx + W*0.14, y: H * 0.23 },
      lel:      { x: cx - W*0.19, y: H * 0.37 },
      rel:      { x: cx + W*0.19, y: H * 0.37 },
      lwr:      { x: cx - W*0.21, y: H * 0.50 },
      rwr:      { x: cx + W*0.21, y: H * 0.50 },
      lhi:      { x: cx - W*0.09, y: H * 0.52 },
      rhi:      { x: cx + W*0.09, y: H * 0.52 },
      lkn:      { x: cx - W*0.09, y: H * 0.70 },
      rkn:      { x: cx + W*0.09, y: H * 0.70 },
      lan:      { x: cx - W*0.09, y: H * 0.87 },
      ran:      { x: cx + W*0.09, y: H * 0.87 },
    };

    // Mapear eventos a articulaciones del mannequin
    const riskJoints = new Set();
    const jointRiskMap = {
      knee_left:    ['lkn'],
      knee_right:   ['rkn'],
      hip_left:     ['lhi'],
      hip_right:    ['rhi'],
      shoulder_left:['lsh'],
      shoulder_right:['rsh'],
      elbow_left:   ['lel'],
      elbow_right:  ['rel'],
      trunk:        ['neck','lsh','rsh','lhi','rhi'],
    };
    events.filter(e => e.frequency > 0).forEach(ev => {
      (jointRiskMap[ev.joint] || []).forEach(j => riskJoints.add(j));
    });

    const connections = [
      ['neck','lsh'],['neck','rsh'],
      ['lsh','lel'],['lel','lwr'],
      ['rsh','rel'],['rel','rwr'],
      ['lsh','lhi'],['rsh','rhi'],
      ['lhi','rhi'],
      ['lhi','lkn'],['lkn','lan'],
      ['rhi','rkn'],['rkn','ran'],
      ['neck','lhi'],['neck','rhi'], // columna aproximada
    ];

    // Dibujar conexiones
    connections.forEach(([a, b]) => {
      const pa = joints[a], pb = joints[b];
      if (!pa || !pb) return;
      const isRisk = riskJoints.has(a) || riskJoints.has(b);
      ctx.save();
      ctx.lineWidth = 3.5;
      ctx.lineCap = 'round';
      ctx.strokeStyle = isRisk ? '#ef4444' : '#f59e0b';
      ctx.shadowColor  = ctx.strokeStyle;
      ctx.shadowBlur   = isRisk ? 10 : 6;
      ctx.beginPath(); ctx.moveTo(pa.x, pa.y); ctx.lineTo(pb.x, pb.y); ctx.stroke();
      ctx.restore();
    });

    // Dibujar nodos
    Object.entries(joints).forEach(([name, p]) => {
      const isRisk = riskJoints.has(name);
      const r = name === 'head' ? 18 : 7;
      ctx.save();
      if (name === 'head') {
        // Disco ámbar de cabeza
        ctx.shadowColor = '#f59e0b'; ctx.shadowBlur = 14;
        ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
        ctx.fillStyle = '#f59e0b'; ctx.fill();
        ctx.strokeStyle = '#fef3c7'; ctx.lineWidth = 2; ctx.stroke();
      } else {
        ctx.shadowColor = isRisk ? '#ef4444' : '#38bdf8';
        ctx.shadowBlur  = isRisk ? 12 : 7;
        ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
        ctx.fillStyle = isRisk ? '#ef4444' : '#38bdf8'; ctx.fill();
        ctx.beginPath(); ctx.arc(p.x, p.y, r * 0.4, 0, Math.PI * 2);
        ctx.fillStyle = '#fff'; ctx.fill();
      }
      // Halo pulsante si hay riesgo
      if (isRisk && name !== 'head') {
        ctx.globalAlpha = 0.35;
        ctx.beginPath(); ctx.arc(p.x, p.y, r + 6, 0, Math.PI * 2);
        ctx.fillStyle = '#ef4444'; ctx.fill();
        ctx.globalAlpha = 1;
      }
      ctx.restore();
    });

    // Leyenda
    ctx.font = 'bold 11px system-ui';
    ctx.fillStyle = '#10b981';
    ctx.fillText('● Normal', 10, H - 24);
    ctx.fillStyle = '#ef4444';
    ctx.fillText('● Desviación', 70, H - 24);
    ctx.fillStyle = '#f59e0b';
    ctx.fillText('● Conexión', 160, H - 24);
  }

  // ── Guardar revisión médica ───────────────────────────────────────────────
  async function saveBiomechDoctorReview() {
    const modal  = $('#biomech-report-modal');
    const savedId = modal?._savedId;
    if (!savedId) {
      showToast('La sesión aún no tiene un ID de servidor. Inténtalo de nuevo.', 'warning');
      return;
    }
    const btn = $('#btn-save-report');
    if (btn) { btn.disabled = true; btn.textContent = 'Guardando...'; }
    try {
      const notes = $('#rep-doctor-notes')?.value?.trim() || '';
      const approved = $('#rep-doctor-approved')?.checked || false;
      const recs = {
        technical:   $('#rec-technical')?.value?.trim()   || '',
        mobility:    $('#rec-mobility')?.value?.trim()    || '',
        strength:    $('#rec-strength')?.value?.trim()    || '',
        stability:   $('#rec-stability')?.value?.trim()   || '',
        flexibility: $('#rec-flexibility')?.value?.trim() || '',
        followup:    $('#rec-followup')?.value?.trim()    || '',
      };
      await api.saveDoctorReview(savedId, {
        doctor_notes: notes,
        is_reviewed_by_doctor: approved,
        preventive_recommendations: recs,
      });
      const statusEl = $('#rep-approval-status');
      if (approved && statusEl) {
        const now = new Date();
        statusEl.textContent = `✅ Aprobado el ${now.toLocaleDateString('es-EC')} a las ${now.toLocaleTimeString('es-EC',{hour:'2-digit',minute:'2-digit'})}`;
        statusEl.style.color = '#10b981';
      }
      showToast('Observaciones y revisión médica guardadas correctamente.', 'success');
    } catch (err) {
      showToast(`No se pudo guardar la revisión: ${err.message}`, 'error');
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = 'Guardar Observaciones'; }
    }
  }

  // ── Historial del atleta ──────────────────────────────────────────────────
  async function openBiomechAthleteHistory() {
    const athleteId = $('#assessment-athlete')?.value;
    if (!athleteId) { showToast('Selecciona un atleta para ver su historial.', 'warning'); return; }
    const modal = $('#athlete-history-modal');
    if (modal) modal.style.display = 'flex';
    const tbody = $('#athlete-history-tbody');
    if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="text-center text-sm text-gray py-4">Cargando...</td></tr>`;
    try {
      const records = await api.getAthleteHistory(athleteId);
      const list = Array.isArray(records) ? records : (records?.results || []);
      if (tbody) {
        tbody.innerHTML = list.length
          ? list.map(item => {
              const events = item.biomechanical_events?.length || 0;
              const reviewed = item.is_reviewed_by_doctor ? '✅ Revisado' : '⏳ Pendiente';
              const riskBadge = item.risk_level === 'high' || item.risk_level === 'critical'
                ? `<span class="badge badge-red">${escapeHtml(riskLabels[item.risk_level] || item.risk_level)}</span>`
                : `<span class="badge badge-blue">${escapeHtml(riskLabels[item.risk_level] || (item.risk_level || 'Bajo'))}</span>`;
              return `<tr>
                <td>${escapeHtml(formatDate(item.session_date))}</td>
                <td>${escapeHtml(EXERCISE_LABELS[item.exercise_type] || item.exercise_type || '—')}</td>
                <td>${item.duration_seconds ? Math.floor(item.duration_seconds/60)+'m '+((item.duration_seconds%60)+'s') : '—'}</td>
                <td>${riskBadge}</td>
                <td>${events}</td>
                <td>${reviewed}</td>
                <td><button class="btn btn-outline btn-sm" data-assessment-action="download" data-assessment-id="${escapeHtml(String(item.id))}">PDF</button></td>
              </tr>`;
            }).join('')
          : `<tr><td colspan="7" class="text-center text-sm text-gray py-4">Sin evaluaciones biomecánicas previas.</td></tr>`;
      }
    } catch (err) {
      if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="text-center text-sm text-gray py-4">Error al cargar: ${escapeHtml(err.message)}</td></tr>`;
    }
  }

  // ── Gestión de umbrales ───────────────────────────────────────────────────
  function openThresholdsModal() {
    const modal = $('#thresholds-modal');
    if (!modal) return;
    modal.style.display = 'flex';
    $('#th-valgus').value          = biomechThresholds.valgus;
    $('#th-trunk').value           = biomechThresholds.trunk;
    $('#th-squat-depth').value     = biomechThresholds.squatDepth;
    $('#th-pushup-elbow').value    = biomechThresholds.pushupElbow;
    $('#th-asymmetry').value       = biomechThresholds.asymmetry;
    $('#th-frames-debounce').value = biomechThresholds.framesDebounce;
  }

  function applyThresholds() {
    biomechThresholds.valgus         = Number($('#th-valgus')?.value)          || DEFAULT_THRESHOLDS.valgus;
    biomechThresholds.trunk          = Number($('#th-trunk')?.value)           || DEFAULT_THRESHOLDS.trunk;
    biomechThresholds.squatDepth     = Number($('#th-squat-depth')?.value)     || DEFAULT_THRESHOLDS.squatDepth;
    biomechThresholds.pushupElbow    = Number($('#th-pushup-elbow')?.value)    || DEFAULT_THRESHOLDS.pushupElbow;
    biomechThresholds.asymmetry      = Number($('#th-asymmetry')?.value)       || DEFAULT_THRESHOLDS.asymmetry;
    biomechThresholds.framesDebounce = Number($('#th-frames-debounce')?.value) || DEFAULT_THRESHOLDS.framesDebounce;
    $('#thresholds-modal').style.display = 'none';
    showToast('Umbrales biomecánicos actualizados.', 'success');
  }

  function resetThresholds() {
    biomechThresholds = { ...DEFAULT_THRESHOLDS };
    openThresholdsModal(); // refrescar valores en inputs
    showToast('Umbrales restablecidos a valores estándar.', 'info');
  }

  // ── PDF desde el modal de informe ─────────────────────────────────────────
  async function downloadBiomechPDF() {
    const modal   = $('#biomech-report-modal');
    const savedId = modal?._savedId;
    if (!savedId) {
      showToast('Guarda las observaciones primero o espera que el backend procese la sesión.', 'warning');
      return;
    }
    try {
      const btn = $('#btn-modal-download-pdf');
      if (btn) { btn.disabled = true; btn.textContent = 'Generando PDF...'; }
      const pdf = await api.getAssessmentPDF(savedId);
      const url = URL.createObjectURL(pdf);
      const link = document.createElement('a');
      link.href = url;
      link.download = `prevenia-biomecanico-${savedId}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
      showToast('PDF biomecánico descargado.', 'success');
    } catch (err) {
      showToast(`No se pudo generar el PDF: ${err.message}`, 'error');
    } finally {
      const btn = $('#btn-modal-download-pdf');
      if (btn) { btn.disabled = false; btn.textContent = 'Descargar PDF Completo'; }
    }
  }

  // ── Wiring de eventos del módulo biomecánico ──────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    // Controles de evaluación
    $('#btn-eval-start')?.addEventListener('click',  startBiomechEval);
    $('#btn-eval-pause')?.addEventListener('click',  pauseBiomechEval);
    $('#btn-eval-resume')?.addEventListener('click', resumeBiomechEval);
    $('#btn-eval-finish')?.addEventListener('click', finishBiomechEval);

    // Botón historial atleta
    $('#btn-athlete-history')?.addEventListener('click', openBiomechAthleteHistory);

    // Botón umbrales
    $('#btn-open-thresholds')?.addEventListener('click', openThresholdsModal);
    $('#btn-save-thresholds')?.addEventListener('click', applyThresholds);
    $('#btn-reset-thresholds')?.addEventListener('click', resetThresholds);
    $('#btn-close-thresholds')?.addEventListener('click', () => {
      $('#thresholds-modal').style.display = 'none';
    });

    // Modal informe
    $('#btn-save-report')?.addEventListener('click', saveBiomechDoctorReview);
    $('#btn-modal-download-pdf')?.addEventListener('click', downloadBiomechPDF);
    // El botón de cierre del modal de informe puede llamarse btn-close-report o btn-close-biomech-report
    const closeReportBtn = $('#btn-close-biomech-report') || $('#btn-close-report');
    closeReportBtn?.addEventListener('click', () => {
      $('#biomech-report-modal').style.display = 'none';
      loadAssessments().catch(() => {});
    });

    // Modal historial
    $('#btn-close-history')?.addEventListener('click', () => {
      $('#athlete-history-modal').style.display = 'none';
    });

    // Cerrar modales al hacer click en el overlay
    ['#biomech-report-modal','#athlete-history-modal','#thresholds-modal'].forEach(sel => {
      $(sel)?.addEventListener('click', e => {
        if (e.target === $(sel)) $(sel).style.display = 'none';
      });
    });

    // Checkbox de aprobación médica – feedback visual inmediato
    $('#rep-doctor-approved')?.addEventListener('change', e => {
      const statusEl = $('#rep-approval-status');
      if (!statusEl) return;
      if (e.target.checked) {
        statusEl.textContent = '⚠ Al guardar, se registrará tu firma digital. Pulsa "Guardar Observaciones".';
        statusEl.style.color = '#f59e0b';
      } else {
        statusEl.textContent = 'Pendiente de aprobación. Al marcar, se registra tu firma digital y fecha de revisión.';
        statusEl.style.color = '';
      }
    });

    // Liberar cámara al ocultar la página de postura
    document.addEventListener('visibilitychange', () => {
      if (document.hidden && biomechSession?.isRunning) {
        pauseBiomechEval();
      }
    });
  });

})();
