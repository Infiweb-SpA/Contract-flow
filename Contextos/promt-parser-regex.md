CONTEXTO:
Soy desarrollador de un sistema Flask que procesa contratos a
honorarios municipales chilenos. El sistema extrae texto de PDFs
y luego usa regex para parsear los datos.

ARCHIVO ACTUAL:
[pegar el código completo de ocr_service.py]

EJEMPLOS DE TEXTO EXTRAÍDO:
--- Contrato 1 (formato propio) ---
[pegar texto]

--- Contrato 2 (externo municipal) ---
[pegar texto]

--- Contrato 3 (otro formato) ---
ACUERDO DE PRESTACIÓN DE SERVICIOS
Universidad Católica de Temuco –Josué Omar RivasVergara
En Temuco, a 09 de Julio de 2021, entre la Universidad Católica de Temuco, RUT 71.918.700-5,
representada en este acto por su Director de Desarrollo de Personas, don Pablo Enrique Palet
Araneda, Cédula Nacional deIdentidadN°10.325.483-3ambosdomiciliadosparaestosefectosen
Manuel Montt N° 056 de la comuna de Temuco, en adelante, “la Universidad”,ydonJosuéOmar
Rivas Vergara de nacionalidad chilena, domiciliado Balmaceda #366, Cunco, cédula nacionalde
identidad N° 20.461.866-6, en adelante “el prestador de servicios”, se ha convenido el siguiente
acuerdo de prestación de servicios profesionales:
PRIMERO: La Universidad acuerda los servicios profesionales de Josué Omar Rivas Vergara
para que preste servicios de Ayudantía (Tutor e-learning) acceso y navegación de la plataforma
EDUCA 2do Semestre, en el marco de Planes de Implementación [PI FID] del Programa de
Fortalecimiento de la Formación Inicial Docente “Modelo Pedagógico para la Formación Inicial
Docente en la UC Temuco: Proceso para la mejora continua acorde a las políticas públicas y las
necesidades de La Araucanía.”, C.Costo: 484-4497
SEGUNDO: El prestador deserviciosseobligaprincipalmenteelapoyosincrónicoconturnosenla
sala de apoyo a estudiantes, como al igual cumplircon las solicitudes de la DTE.
El no cumplimiento de estas obligaciones, conlleva la resolución del Acuerdo de Prestación de
Servicios.
TERCERO: LaUniversidadsecomprometeapagaralprestadorlasumatotalde$222.000,porel
acompañamiento para docentes y estudiantes en el acceso y navegación de la plataforma
EDUCA segundo semestre, honorarios que se pagarán, según el siguiente calendario:
Cuota Valor Cuota Mes de pago
1 $ 37.000 Agosto
2 $ 37.000 Septiembre
3 $ 37.000 Octubre
4 $ 37.000 Noviembre
5 $ 37.000 Diciembre
6 $ 37.000 Enero 2022
Total $ 222.000.-
De la suma antes referida, la Universidad descontará y retendrá un 11,5%, correspondiente al
impuesto respectivo y contra y previa emisión del prestador de la correspondiente boleta de
honorarios profesionales.
CUARTO: El presente Acuerdo de prestación de servicios Profesionales regirá desde el desdeel
01 de agosto de 2021 al 31 deenerode2022,sinperjuiciodeltérminoanticipadoenelsupuesto
de la cláusula segunda del presente acuerdo.
La Universidad, en cualquier momento, podrá dar por terminado anticipadamente el presente
Acuerdo sin responsabilidad para ésta, y sin necesidad de que medie resolución judicial alguna,
dando aviso por escrito al prestador con treinta días de anticipación. En este caso,laUniversidad
deberá cubrir loshonorariosquecorrespondanporlosserviciosprestadosyquehayarecibidoasu
enterasatisfacción. Asimismo,elPrestadorpodrádarloporconcluidodemaneraanticipada,previo
aviso escrito de 30 días. La Universidadsereservaelderechodeaceptareltérminoanticipadodel
Acuerdo sin que ello implique la renuncia a deducirlas acciones legales que, en su caso, proceda.
QUINTO: El prestador de servicios deberá entregar a la Universidad una boletadehonorariospor
el monto señalado en el punto TERCERO, antes del día 5 del mes. Si el profesional no hiciera
entrega de la boleta de honorarios en la fecha estipulada, la Universidad pagará el honorario
correspondiente,almessiguiente,siempreycuandoelprofesionalhubierehechoentregaoportuna
de la nueva boleta de honorarios.
SEXTO: En caso de controversia y no pudiendo llegar a un acuerdo de manera amigable y en
atención a los efectos del contrato, las partes fijan domicilio en la comuna y ciudad de Temuco,
sometiéndose a la competencia de sus tribunales ordinariosde justicia.
SEPTIMO: El prestador deserviciosnopodrácederesteAcuerdoosubcontratarningunapartedel
mismo, sin el consentimiento previo por escrito dela Universidad.
OCTAVO: El prestador tendrá la obligación de guardar irrestricta confidencialidad de toda
información generada por la Universidad, sin perjuicio de la eventual autorización que ésta
establezca para difundir dicha información. Esta obligación se extiende durante la vigencia del
presente acuerdo e inclusive por 12 meses posteriores a la fecha de término del acuerdo. El
incumplimiento de esta obligación facultará a la Universidad a poner término al presenteacuerdo,
sin perjuicio de las acciones legales que pudieranejercerse.
NOVENO: Las partes dejan constancia que el presente acuerdo no constituye un contrato de
trabajo,dejandoconstanciaqueexisteunaprestacióndeservicioendondenoexistesubordinación
y dependencia. En consecuencia, las relaciones entre las partes no se regirán por las normasdel
Código del Trabajo sino por el presente acuerdo ypor el Código Civil.
DECIMO: El presente convenio se firma en cuatro ejemplares, quedando uno en poder del
prestador y los tres restantes para la Universidad.
UNDECIMO: Las partes acuerdan, que para todos los efectos que puedan derivarse del presente
contrato, fijan domicilio convencional en la ciudad de TEMUCO, y se someten desde ya a la
jurisdicción de sus Tribunales Ordinarios de Justicia.
Prestador de Servicios Universidad Católica de Temuco
Josué Omar Rivas Vergara Director de Desarrollo de Personas
RUT: 20.461.866-6 Pablo Enrique Palet Araneda

CAMPOS A EXTRAER:
[listar los 10 campos]

CONTEXTO LEGAL:
[lo que expliqué arriba]

PEDIDO:
Mejora las funciones parse_contract_data() y extract_functions()
para que detecten correctamente los datos en todos los formatos
de contrato mostrados. Devuélveme las funciones completas
reemplazables con comentarios explicativos.