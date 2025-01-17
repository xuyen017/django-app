document.addEventListener('DOMContentLoaded', function() {
    const alertMessage = document.getElementById('alert-message');
    if (alertMessage) {
        setTimeout(() => {
            alertMessage.style.transition = 'opacity 0.5s ease';
            alertMessage.style.opacity = '0'; // Làm mờ dần
            setTimeout(() => alertMessage.remove(), 500); // Xóa khỏi DOM sau khi mờ
        }, 3000); 
    }
});
document.addEventListener('DOMContentLoaded', function() {
    const footer = document.getElementById('page-footer');
    window.addEventListener('scroll', function() {
        if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 10) {
            // Hiển thị footer khi người dùng cuộn đến gần cuối trang
            footer.style.display = 'block';
        } else {
            // Ẩn footer khi không ở gần cuối trang
            footer.style.display = 'none';
        }
    });
});