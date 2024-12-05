let slideIndex = 1;
showSlides(slideIndex);

// Cambia de imagen con botones "anterior" y "siguiente"
function plusSlides(n) {
  showSlides(slideIndex += n);
}

// Muestra una imagen específica
function currentSlide(n) {
  showSlides(slideIndex = n);
}

function showSlides(n) {
  let i;
  let slides = document.getElementsByClassName("mySlides");
  let dots = document.getElementsByClassName("dot");

  if (n > slides.length) {slideIndex = 1} // Vuelve al inicio si supera el número de imágenes
  if (n < 1) {slideIndex = slides.length} // Va al final si es menor a 1

  for (i = 0; i < slides.length; i++) {
    slides[i].style.display = "none"; // Oculta todas las imágenes
  }

  for (i = 0; i < dots.length; i++) {
    dots[i].className = dots[i].className.replace(" active", ""); // Elimina la clase activa
  }

  slides[slideIndex-1].style.display = "block"; // Muestra la imagen actual
  dots[slideIndex-1].className += " active"; // Activa el punto correspondiente
}

function abrirChatbot() {
    window.open('http://localhost:8502/', '_blank');
}
        
