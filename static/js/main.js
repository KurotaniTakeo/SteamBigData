/**
* Template Name: Mamba - v2.0.1
* Template URL: https://bootstrapmade.com/mamba-one-page-bootstrap-template-free/
* Author: BootstrapMade.com
* License: https://bootstrapmade.com/license/
* Change time：2025-4-12
* Apply to my project SDRS：https://github.com/Tarheee/SDRS
*/
!(function($) {
  "use strict";

  // Toggle .header-scrolled class to #header when page is scrolled
  $(window).scroll(function() {
    if ($(this).scrollTop() > 100) {
      $('#header').addClass('header-scrolled');
    } else {
      $('#header').removeClass('header-scrolled');
    }
  });

  if ($(window).scrollTop() > 100) {
    $('#header').addClass('header-scrolled');
  }

  // Stick the header at top on scroll
  $("#header").sticky({
    topSpacing: 0,
    zIndex: '50'
  });

  // Smooth scroll for the navigation menu and links with .scrollto classes
  $(document).on('click', '.nav-menu a, .mobile-nav a, .scrollto', function(e) {
    if (location.pathname.replace(/^\//, '') == this.pathname.replace(/^\//, '') && location.hostname == this.hostname) {
      e.preventDefault();
      var target = $(this.hash);
      if (target.length) {

        var scrollto = target.offset().top;
        var scrolled = 2;

        if ($('#header-sticky-wrapper').length) {
          scrollto -= $('#header-sticky-wrapper').outerHeight() - scrolled;
        }

        if ($(this).attr("href") == '#header') {
          scrollto = 0;
        }

        $('html, body').animate({
          scrollTop: scrollto
        }, 1500, 'easeInOutExpo');

        if ($(this).parents('.nav-menu, .mobile-nav').length) {
          $('.nav-menu .active, .mobile-nav .active').removeClass('active');
          $(this).closest('li').addClass('active');
        }

        if ($('body').hasClass('mobile-nav-active')) {
          $('body').removeClass('mobile-nav-active');
          $('.mobile-nav-toggle i').toggleClass('icofont-navigation-menu icofont-close');
          $('.mobile-nav-overly').fadeOut();
        }
        return false;
      }
    }
  });

 // Mobile Navigation
  if ($('.nav-menu').length) {
    var $mobile_nav = $('.nav-menu').clone().prop({
      class: 'mobile-nav d-lg-none'
    });
    $('body').append($mobile_nav);
    $('body').prepend('<button type="button" class="mobile-nav-toggle d-lg-none"><i class="icofont-navigation-menu"></i></button>');
    $('body').append('<div class="mobile-nav-overly"></div>');

    $(document).on('click', '.mobile-nav-toggle', function(e) {
      $('body').toggleClass('mobile-nav-active');
      $('.mobile-nav-toggle i').toggleClass('icofont-navigation-menu icofont-close');
      $('.mobile-nav-overly').toggle();
    });

    $(document).on('click', '.mobile-nav .drop-down > a', function(e) {
      e.preventDefault();
      $(this).next().slideToggle(300);
      $(this).parent().toggleClass('active');
    });

    $(document).click(function(e) {
      var container = $(".mobile-nav, .mobile-nav-toggle");
      if (!container.is(e.target) && container.has(e.target).length === 0) {
        if ($('body').hasClass('mobile-nav-active')) {
          $('body').removeClass('mobile-nav-active');
          $('.mobile-nav-toggle i').toggleClass('icofont-navigation-menu icofont-close');
          $('.mobile-nav-overly').fadeOut();
        }
      }
    });
  } else if ($(".mobile-nav, .mobile-nav-toggle").length) {
    $(".mobile-nav, .mobile-nav-toggle").hide();
  }

  // Intro carousel
  var heroCarousel = $("#heroCarousel");
  var heroCarouselIndicators = $("#hero-carousel-indicators");
  heroCarousel.find(".carousel-inner").children(".carousel-item").each(function(index) {
    (index === 0) ?
    heroCarouselIndicators.append("<li data-target='#heroCarousel' data-slide-to='" + index + "' class='active'></li>"):
      heroCarouselIndicators.append("<li data-target='#heroCarousel' data-slide-to='" + index + "'></li>");
  });

  heroCarousel.on('slid.bs.carousel', function(e) {
    $(this).find('h2').addClass('animated fadeInDown');
    $(this).find('p').addClass('animated fadeInUp');
    $(this).find('.btn-get-started').addClass('animated fadeInUp');
  });

  // Back to top button
  $(window).scroll(function() {
    if ($(this).scrollTop() > 100) {
      $('.back-to-top').fadeIn('slow');
    } else {
      $('.back-to-top').fadeOut('slow');
    }
  });

  $('.back-to-top').click(function() {
    $('html, body').animate({
      scrollTop: 0
    }, 1500, 'easeInOutExpo');
    return false;
  });

  // Initiate the venobox plugin
  $(window).on('load', function() {
    $('.venobox').venobox();
  });

  // jQuery counterUp
  $('[data-toggle="counter-up"]').counterUp({
    delay: 10,
    time: 1000
  });

  // Porfolio isotope and filter
  $(window).on('load', function() {
    var srsIsotope = $('.srs-container').isotope({
      itemSelector: '.srs-item',
      layoutMode: 'fitRows'
    });

    $('#srs-flters li').on('click', function() {
      $("#srs-flters li").removeClass('filter-active');
      $(this).addClass('filter-active');

      srsIsotope.isotope({
        filter: $(this).data('filter')
      });
    });

    // Initiate venobox (lightbox feature used in portofilo)
    $(document).ready(function() {
      $('.venobox').venobox();
    });
  });

  // Initi AOS
  AOS.init({
    duration: 1000,
    easing: "ease-in-out-back"
  });


  })(jQuery);




document.addEventListener('DOMContentLoaded', function() {
  const delayRedirect = document.querySelector('body').getAttribute('data-delay-redirect') === 'true';

  if (delayRedirect) {
    setTimeout(function() {
      window.location.href = "/"; // 跳转地址设置为1秒后
    }, 1000);
  }

  // 自动关闭 alert
  const alerts = document.querySelectorAll('.alert-dismissible');
  alerts.forEach(alert => {
    setTimeout(() => {
      alert.style.display = 'none';// 显示消息为持续1秒后自动关闭
    }, 1000);
  });
});


//偏好完善度：使用 data 属性存储原始值
$(document).ready(function() {
  $('[data-toggle="counter-up"]').each(function() {
    var $this = $(this),
        value = $this.data('value');

    $({countNum: 0}).animate({countNum: value}, {
      duration: 2000,
      easing: 'swing',
      step: function() {
        $this.text(Math.ceil(this.countNum) + '%');
      }
    });
  });
});




//perferenc.html动画
function createCloneAndDrop(original, targetContainer) {
  const rect = original.getBoundingClientRect();
  const clone = original.cloneNode(true);
  const scrollTop = window.scrollY || document.documentElement.scrollTop;
  const scrollLeft = window.scrollX || document.documentElement.scrollLeft;

  clone.style.position = 'absolute';
  clone.style.top = rect.top + scrollTop + 'px';
  clone.style.left = rect.left + scrollLeft + 'px';
  clone.style.zIndex = 1000;
  clone.style.transition = 'transform 0.6s ease-in, opacity 1s';
  clone.style.opacity = '1';

  document.body.appendChild(clone);

  // 初始掉落
  setTimeout(() => {
    clone.style.transform = 'translateY(200px)';
  }, 10);

  // 弹起
  setTimeout(() => {
    clone.style.transition = 'transform 0.3s ease-out';
    clone.style.transform = 'translateY(160px)';
  }, 600);

  // 再下落
  setTimeout(() => {
    clone.style.transition = 'transform 0.3s ease-in, opacity 0.5s';
    clone.style.transform = 'translateY(300px)';
    clone.style.opacity = '0';
  }, 900);

  // 加入最终容器
setTimeout(() => {
  document.body.removeChild(clone);

  // 🛑 关键：添加前检查 bubble 是否仍被选中
  if (original.classList.contains('selected')) {
const tag = original.cloneNode(true);
tag.classList.add('selected');
tag.setAttribute('data-label', original.textContent.trim());

// ✅ 保留原有的 data-type
const dataType = original.getAttribute('data-type');
if (dataType) {
  tag.setAttribute('data-type', dataType);
}

targetContainer.appendChild(tag);

  }

}, 1300);

}
document.addEventListener('DOMContentLoaded', () => {
  const bubbles = document.querySelectorAll('.bubble');
  const selectionBox = document.getElementById('selection-container');

  // ⚠️ 页面加载后先进行回显（只影响 UI 状态，不触发点击）
  bubbles.forEach(bubble => {
    const type = bubble.getAttribute('data-type');
    const value = bubble.textContent.trim();

    if (existingPreferences[type] && existingPreferences[type].includes(value)) {
      bubble.classList.add('selected');

      // 添加到下方区域，但不使用动画（createCloneAndDrop 会有时序问题）
      const tag = bubble.cloneNode(true);
      tag.classList.remove('selected'); // ❗不要保留 .selected，避免影响点击逻辑
      tag.setAttribute('data-label', value);
      tag.setAttribute('data-type', type);
      selectionBox.appendChild(tag);
    }
  });

  // ✅ 然后再绑定点击事件（避免和上面逻辑冲突）
  bubbles.forEach(bubble => {
    bubble.addEventListener('click', () => {
      const label = bubble.textContent.trim();
      const type = bubble.getAttribute('data-type');

      if (!bubble.classList.contains('selected')) {
        bubble.classList.add('selected');
        createCloneAndDrop(bubble, selectionBox);
      } else {
        bubble.classList.remove('selected');

        // 移除下方匹配的克隆标签
        const toRemove = selectionBox.querySelectorAll(`.bubble[data-label="${label}"]`);
        toRemove.forEach(tag => tag.remove());
      }
    });
  });

  // 清空按钮逻辑
  document.getElementById('clear-btn').addEventListener('click', () => {
    selectionBox.innerHTML = '';
    document.querySelectorAll('.bubble.selected').forEach(bubble => {
      bubble.classList.remove('selected');
    });
  });

  // 提交逻辑
  document.getElementById('submit-preference').addEventListener('click', async () => {
    const selections = {
      genre: [],
      category: [],
      price: [],
      platform: []
    };

    document.querySelectorAll('#selection-container .bubble').forEach(bubble => {
      const type = bubble.getAttribute('data-type');
      const value = bubble.textContent.trim();

      if(type === 'genre') selections.genre.push(value);
      else if(type === 'category') selections.category.push(value);
      else if(type === 'price') selections.price.push(value);
      else if(type === 'platform') selections.platform.push(value);
    });

    try {
      const response = await fetch('/submit-preferences', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(selections)
      });

      if(response.ok) {
        alert('偏好设置已保存！');
      }
    } catch (error) {
      console.error('保存失败:', error);
    }
  });

  // 图标弹窗逻辑
  document.addEventListener('click', function (e) {
    document.querySelectorAll('.icon-with-popup .popup').forEach(p => p.style.display = 'none');

    const iconBox = e.target.closest('.icon-with-popup');
    if (iconBox) {
      const popup = iconBox.querySelector('.popup');
      popup.style.display = 'block';
    }
  });
});

document.addEventListener('DOMContentLoaded', function () {
    document.getElementById('refresh-btn').addEventListener('click', function() {
        fetch('/refresh_recommendations', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            alert(data.message);
            if (data.status === 'success') {
                location.reload();
            }
        })
        .catch(error => {
            alert("请求失败：" + error);
        });
    });
});


