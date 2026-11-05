// @types/prismjs no cubre los módulos de gramática individuales. Se importan solo por su efecto
// (registran el lenguaje en el Prism global); no exponen API tipada.
declare module "prismjs/components/*";
