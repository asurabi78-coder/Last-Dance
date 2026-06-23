# 섹션별 HTML/React 템플릿

## 1. 히어로 섹션 HTML 템플릿 (이커머스용)

```html
<!-- 히어로: 제품 이미지 갤러리 -->
<section class="product-hero" aria-label="제품 이미지">
  <div class="product-hero__gallery">
    <!-- 메인 이미지 -->
    <div class="product-hero__main">
      <img
        id="mainImage"
        src="images/main-01.webp"
        alt="[제품명] 정면 이미지"
        width="860"
        height="860"
        class="product-hero__img"
      />
      <!-- 확대 렌즈 (데스크톱) -->
      <div class="product-hero__zoom" id="zoomLens" aria-hidden="true"></div>
    </div>

    <!-- 썸네일 네비게이션 -->
    <div class="product-hero__thumbs" role="list" aria-label="제품 이미지 목록">
      <button
        class="product-hero__thumb product-hero__thumb--active"
        role="listitem"
        aria-current="true"
        onclick="changeImage('images/main-01.webp', this)"
      >
        <img src="images/main-01-thumb.webp" alt="정면" width="80" height="80" />
      </button>
      <button
        class="product-hero__thumb"
        role="listitem"
        onclick="changeImage('images/main-02.webp', this)"
      >
        <img src="images/main-02-thumb.webp" alt="후면" width="80" height="80" />
      </button>
      <button
        class="product-hero__thumb"
        role="listitem"
        onclick="changeImage('images/main-03.webp', this)"
      >
        <img src="images/main-03-thumb.webp" alt="측면" width="80" height="80" />
      </button>
      <!-- 동영상 썸네일 -->
      <button
        class="product-hero__thumb product-hero__thumb--video"
        role="listitem"
        onclick="playVideo()"
      >
        <img src="images/video-thumb.webp" alt="제품 소개 영상" width="80" height="80" />
        <span class="product-hero__play-icon" aria-hidden="true">&#9654;</span>
      </button>
    </div>
  </div>
</section>
```

---

## 2. 제품 정보 섹션 HTML 템플릿

```html
<!-- 제품 기본 정보 -->
<section class="product-info" aria-label="제품 정보">
  <!-- 브랜드 -->
  <a href="/brand/moai" class="product-info__brand">[브랜드명]</a>

  <!-- 제품명 -->
  <h1 class="product-info__title">[제품명을 여기에 입력한다]</h1>

  <!-- 평점 -->
  <div class="product-info__rating" aria-label="평점 4.8점, 리뷰 3241개">
    <div class="product-info__stars" aria-hidden="true">
      <span class="star star--filled">&#9733;</span>
      <span class="star star--filled">&#9733;</span>
      <span class="star star--filled">&#9733;</span>
      <span class="star star--filled">&#9733;</span>
      <span class="star star--half">&#9733;</span>
    </div>
    <span class="product-info__rating-value">4.8</span>
    <a href="#reviews" class="product-info__review-count">(3,241)</a>
  </div>

  <!-- 가격 -->
  <div class="product-info__price-wrap">
    <span class="product-info__discount-badge" aria-label="30% 할인">30%</span>
    <span class="product-info__price" aria-label="판매가 89,900원">
      <strong>89,900</strong><small>원</small>
    </span>
    <span class="product-info__original-price" aria-label="정가 129,000원">
      <del>129,000원</del>
    </span>
  </div>

  <!-- 배송 정보 -->
  <div class="product-info__shipping">
    <span class="product-info__shipping-badge">무료배송</span>
    <span class="product-info__delivery">내일(수) 도착 예정</span>
  </div>

  <!-- 적립금 -->
  <div class="product-info__points">
    <span>적립</span>
    <strong>899P</strong>
    <small>(1%)</small>
  </div>

  <!-- 옵션 선택 -->
  <div class="product-info__options">
    <label for="colorSelect" class="product-info__option-label">색상 선택</label>
    <div class="product-info__color-swatches" role="radiogroup" aria-label="색상 선택">
      <button
        class="product-info__swatch product-info__swatch--active"
        role="radio"
        aria-checked="true"
        aria-label="화이트"
        style="background-color: #FFFFFF; border: 2px solid #333;"
        onclick="selectColor('white', this)"
      ></button>
      <button
        class="product-info__swatch"
        role="radio"
        aria-checked="false"
        aria-label="그레이"
        style="background-color: #888888;"
        onclick="selectColor('gray', this)"
      ></button>
      <button
        class="product-info__swatch product-info__swatch--disabled"
        role="radio"
        aria-checked="false"
        aria-disabled="true"
        aria-label="민트 품절"
        style="background-color: #98D8C8;"
        title="품절"
      ></button>
    </div>

    <!-- 수량 선택 -->
    <div class="product-info__quantity">
      <label for="quantity">수량</label>
      <div class="product-info__quantity-control">
        <button
          class="product-info__qty-btn"
          onclick="changeQty(-1)"
          aria-label="수량 감소"
        >-</button>
        <input
          type="number"
          id="quantity"
          value="1"
          min="1"
          max="99"
          class="product-info__qty-input"
          aria-label="수량"
        />
        <button
          class="product-info__qty-btn"
          onclick="changeQty(1)"
          aria-label="수량 증가"
        >+</button>
      </div>
    </div>
  </div>

  <!-- CTA 버튼 -->
  <div class="product-info__cta">
    <button class="btn-secondary product-info__cart-btn" onclick="addToCart()">
      장바구니 담기
    </button>
    <button class="btn-primary product-info__buy-btn" onclick="buyNow()">
      바로 구매하기
    </button>
  </div>

  <!-- 찜하기 -->
  <button class="product-info__wish" onclick="toggleWish()" aria-label="찜하기">
    <span class="product-info__wish-icon" aria-hidden="true">&#9825;</span>
    <span>찜하기</span>
    <span class="product-info__wish-count">1,234</span>
  </button>
</section>
```

---

## 3. 탭 메뉴 HTML 템플릿

```html
<!-- 탭 메뉴 (스티키) -->
<nav class="tab-menu" role="tablist" aria-label="상품 정보 탭" id="tabMenu">
  <button
    class="tab-menu__tab tab-menu__tab--active"
    role="tab"
    id="tab-detail"
    aria-selected="true"
    aria-controls="panel-detail"
    onclick="switchTab('detail')"
  >
    상세정보
  </button>
  <button
    class="tab-menu__tab"
    role="tab"
    id="tab-reviews"
    aria-selected="false"
    aria-controls="panel-reviews"
    onclick="switchTab('reviews')"
  >
    후기 <span class="tab-menu__count">3,241</span>
  </button>
  <button
    class="tab-menu__tab"
    role="tab"
    id="tab-faq"
    aria-selected="false"
    aria-controls="panel-faq"
    onclick="switchTab('faq')"
  >
    FAQ
  </button>
</nav>

<!-- 탭 패널: 상세정보 -->
<div
  class="tab-panel"
  role="tabpanel"
  id="panel-detail"
  aria-labelledby="tab-detail"
>
  <!-- 상세정보 콘텐츠 삽입 -->
</div>

<!-- 탭 패널: 후기 -->
<div
  class="tab-panel tab-panel--hidden"
  role="tabpanel"
  id="panel-reviews"
  aria-labelledby="tab-reviews"
  hidden
>
  <!-- 후기 콘텐츠 삽입 -->
</div>

<!-- 탭 패널: FAQ -->
<div
  class="tab-panel tab-panel--hidden"
  role="tabpanel"
  id="panel-faq"
  aria-labelledby="tab-faq"
  hidden
>
  <!-- FAQ 콘텐츠 삽입 -->
</div>
```

---

## 4. 후기 섹션 HTML 템플릿

```html
<!-- 후기 섹션 -->
<section class="reviews" id="reviews" aria-label="고객 후기">
  <!-- 평점 요약 -->
  <div class="reviews__summary">
    <div class="reviews__score">
      <span class="reviews__score-value">4.8</span>
      <div class="reviews__stars" aria-hidden="true">&#9733;&#9733;&#9733;&#9733;&#9734;</div>
      <span class="reviews__total">총 3,241개 후기</span>
    </div>

    <!-- 평점 분포 -->
    <div class="reviews__distribution" aria-label="평점 분포">
      <div class="reviews__bar-row">
        <span>5점</span>
        <div class="reviews__bar">
          <div class="reviews__bar-fill" style="width: 72%;" aria-label="72%"></div>
        </div>
        <span>2,334</span>
      </div>
      <div class="reviews__bar-row">
        <span>4점</span>
        <div class="reviews__bar">
          <div class="reviews__bar-fill" style="width: 18%;" aria-label="18%"></div>
        </div>
        <span>583</span>
      </div>
      <div class="reviews__bar-row">
        <span>3점</span>
        <div class="reviews__bar">
          <div class="reviews__bar-fill" style="width: 6%;" aria-label="6%"></div>
        </div>
        <span>195</span>
      </div>
      <div class="reviews__bar-row">
        <span>2점</span>
        <div class="reviews__bar">
          <div class="reviews__bar-fill" style="width: 3%;" aria-label="3%"></div>
        </div>
        <span>97</span>
      </div>
      <div class="reviews__bar-row">
        <span>1점</span>
        <div class="reviews__bar">
          <div class="reviews__bar-fill" style="width: 1%;" aria-label="1%"></div>
        </div>
        <span>32</span>
      </div>
    </div>
  </div>

  <!-- 후기 필터 -->
  <div class="reviews__filters" role="toolbar" aria-label="후기 필터">
    <button class="reviews__filter reviews__filter--active" aria-pressed="true">전체</button>
    <button class="reviews__filter" aria-pressed="false">포토후기</button>
    <button class="reviews__filter" aria-pressed="false">5점</button>
    <button class="reviews__filter" aria-pressed="false">4점</button>
    <button class="reviews__filter" aria-pressed="false">3점 이하</button>
  </div>

  <!-- 후기 정렬 -->
  <div class="reviews__sort">
    <select aria-label="후기 정렬">
      <option value="recent" selected>최신순</option>
      <option value="rating-high">평점 높은순</option>
      <option value="helpful">도움순</option>
    </select>
  </div>

  <!-- 개별 후기 카드 -->
  <article class="reviews__card" aria-label="고객 후기">
    <div class="reviews__card-header">
      <div class="reviews__card-stars" aria-label="5점">&#9733;&#9733;&#9733;&#9733;&#9733;</div>
      <span class="reviews__card-author">홍*동</span>
      <span class="reviews__card-date">2026.04.05</span>
    </div>
    <div class="reviews__card-option">
      <span>구매 옵션: 화이트</span>
    </div>
    <p class="reviews__card-text">
      밤새 가습해도 물이 남아있어서 좋습니다. 소음도 거의 없고 디자인도 깔끔해요.
      아침에 일어나면 피부가 확실히 다릅니다.
    </p>
    <!-- 후기 이미지 -->
    <div class="reviews__card-images">
      <button class="reviews__card-img-btn" onclick="openLightbox(0)">
        <img src="review-img-01.webp" alt="후기 이미지 1" width="80" height="80" loading="lazy" />
      </button>
      <button class="reviews__card-img-btn" onclick="openLightbox(1)">
        <img src="review-img-02.webp" alt="후기 이미지 2" width="80" height="80" loading="lazy" />
      </button>
    </div>
    <button class="reviews__card-helpful" onclick="markHelpful(this)">
      도움됐어요 <span>24</span>
    </button>
  </article>

  <!-- 페이지네이션 -->
  <nav class="reviews__pagination" aria-label="후기 페이지">
    <button class="reviews__page reviews__page--active" aria-current="page">1</button>
    <button class="reviews__page">2</button>
    <button class="reviews__page">3</button>
    <button class="reviews__page">...</button>
    <button class="reviews__page">325</button>
  </nav>
</section>
```

---

## 5. FAQ 아코디언 HTML 템플릿

```html
<!-- FAQ 아코디언 -->
<section class="faq" id="faq" aria-label="자주 묻는 질문">
  <h2 class="faq__title">자주 묻는 질문</h2>

  <div class="faq__list">
    <!-- FAQ 항목 1 -->
    <div class="faq__item">
      <button
        class="faq__question"
        aria-expanded="false"
        aria-controls="faq-answer-1"
        onclick="toggleFaq(this)"
      >
        <span>배송은 얼마나 걸리나요?</span>
        <span class="faq__icon" aria-hidden="true">+</span>
      </button>
      <div class="faq__answer" id="faq-answer-1" hidden>
        <p>
          평일 오후 2시 이전 주문 시 당일 출고되며, 출고 후 1~2일 내 수령 가능합니다.
          제주/도서산간 지역은 1~2일 추가 소요됩니다. 무료배송이며 추가 비용은 없습니다.
        </p>
      </div>
    </div>

    <!-- FAQ 항목 2 -->
    <div class="faq__item">
      <button
        class="faq__question"
        aria-expanded="false"
        aria-controls="faq-answer-2"
        onclick="toggleFaq(this)"
      >
        <span>교환/반품은 어떻게 하나요?</span>
        <span class="faq__icon" aria-hidden="true">+</span>
      </button>
      <div class="faq__answer" id="faq-answer-2" hidden>
        <p>
          수령 후 7일 이내 교환/반품 접수 가능합니다. 단순 변심 시 왕복 배송비 5,000원이
          부과되며, 상품 하자 시 무료 교환/반품됩니다. 고객센터(1577-XXXX) 또는
          카카오톡 채널로 접수하면 됩니다.
        </p>
      </div>
    </div>

    <!-- FAQ 항목 3 -->
    <div class="faq__item">
      <button
        class="faq__question"
        aria-expanded="false"
        aria-controls="faq-answer-3"
        onclick="toggleFaq(this)"
      >
        <span>세척은 어떻게 하나요?</span>
        <span class="faq__icon" aria-hidden="true">+</span>
      </button>
      <div class="faq__answer" id="faq-answer-3" hidden>
        <p>
          물통, 본체, 진동자 3파트 분리 세척이 가능합니다. 물통은 매일 헹구고,
          진동자는 주 1회 식초물(1:10 비율)로 세척 권장합니다. 상세 세척 방법은
          동봉된 사용설명서를 참고하면 됩니다.
        </p>
      </div>
    </div>

    <!-- FAQ 항목 4 -->
    <div class="faq__item">
      <button
        class="faq__question"
        aria-expanded="false"
        aria-controls="faq-answer-4"
        onclick="toggleFaq(this)"
      >
        <span>A/S 기간은 얼마인가요?</span>
        <span class="faq__icon" aria-hidden="true">+</span>
      </button>
      <div class="faq__answer" id="faq-answer-4" hidden>
        <p>
          구매일로부터 1년간 무상 A/S가 제공됩니다. 무상 기간 이후에도 유상 수리가
          가능하며, 주요 부품은 3년간 보유합니다. A/S 접수는 고객센터(1577-XXXX)로
          문의하면 됩니다.
        </p>
      </div>
    </div>

    <!-- FAQ 항목 5 -->
    <div class="faq__item">
      <button
        class="faq__question"
        aria-expanded="false"
        aria-controls="faq-answer-5"
        onclick="toggleFaq(this)"
      >
        <span>추가 비용이 있나요?</span>
        <span class="faq__icon" aria-hidden="true">+</span>
      </button>
      <div class="faq__answer" id="faq-answer-5" hidden>
        <p>
          표시된 가격 외 추가 비용은 없습니다. 무료배송이며 설치비도 없습니다.
          다만 제주/도서산간 지역은 추가 배송비 3,000원이 부과될 수 있습니다.
        </p>
      </div>
    </div>
  </div>
</section>
```

---

## 6. 관련 제품 그리드 HTML 템플릿

```html
<!-- 관련 제품 추천 -->
<section class="related" aria-label="관련 제품">
  <h2 class="related__title">이 제품과 함께 많이 구매한 상품</h2>

  <div class="related__grid">
    <!-- 관련 제품 카드 -->
    <a href="/product/002" class="related__card">
      <div class="related__img-wrap">
        <img
          src="images/related-01.webp"
          alt="[관련 제품명]"
          width="200"
          height="200"
          loading="lazy"
        />
      </div>
      <div class="related__info">
        <span class="related__brand">[브랜드]</span>
        <h3 class="related__name">[관련 제품명]</h3>
        <div class="related__price">
          <span class="related__discount">20%</span>
          <strong>39,900원</strong>
        </div>
        <div class="related__rating">
          <span aria-hidden="true">&#9733;</span>
          <span>4.6</span>
          <span class="related__review-count">(892)</span>
        </div>
      </div>
    </a>

    <!-- 나머지 카드 3개 동일 구조로 반복 -->
  </div>
</section>
```

---

## 7. 모바일 하단 고정 바 HTML 템플릿

```html
<!-- 모바일 하단 고정 CTA 바 -->
<div class="mobile-bottom-bar" id="mobileBottomBar" aria-label="구매 버튼">
  <button class="mobile-bottom-bar__cart" onclick="addToCart()" aria-label="장바구니 담기">
    <span class="mobile-bottom-bar__cart-icon" aria-hidden="true">&#128722;</span>
    장바구니
  </button>
  <button class="mobile-bottom-bar__buy" onclick="buyNow()">
    바로 구매하기
  </button>
</div>
```

---

## 8. React 컴포넌트 템플릿

### ProductImage.tsx

```tsx
'use client';

import { useState, useCallback } from 'react';
import Image from 'next/image';
import styles from './product-detail.module.css';

interface ProductImageProps {
  images: {
    src: string;
    alt: string;
    type: 'image' | 'video';
  }[];
}

/** 제품 이미지 갤러리 컴포넌트 */
export default function ProductImage({ images }: ProductImageProps) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [isZoomed, setIsZoomed] = useState(false);

  const handleThumbnailClick = useCallback((index: number) => {
    setActiveIndex(index);
    setIsZoomed(false);
  }, []);

  const handleSwipe = useCallback((direction: 'left' | 'right') => {
    setActiveIndex((prev) => {
      if (direction === 'left') return Math.min(prev + 1, images.length - 1);
      return Math.max(prev - 1, 0);
    });
  }, [images.length]);

  return (
    <section className={styles.hero} aria-label="제품 이미지">
      {/* 메인 이미지 */}
      <div
        className={styles.heroMain}
        onClick={() => setIsZoomed(!isZoomed)}
        role="button"
        aria-label={isZoomed ? '축소' : '확대'}
        tabIndex={0}
      >
        <Image
          src={images[activeIndex].src}
          alt={images[activeIndex].alt}
          width={860}
          height={860}
          priority={activeIndex === 0}
          className={`${styles.heroImg} ${isZoomed ? styles.heroImgZoomed : ''}`}
        />
      </div>

      {/* 인디케이터 (모바일) */}
      <div className={styles.heroIndicators} aria-hidden="true">
        {images.map((_, i) => (
          <span
            key={i}
            className={`${styles.heroDot} ${i === activeIndex ? styles.heroDotActive : ''}`}
          />
        ))}
      </div>

      {/* 썸네일 (데스크톱) */}
      <div className={styles.heroThumbs} role="list" aria-label="이미지 목록">
        {images.map((img, i) => (
          <button
            key={i}
            className={`${styles.heroThumb} ${i === activeIndex ? styles.heroThumbActive : ''}`}
            role="listitem"
            aria-current={i === activeIndex}
            onClick={() => handleThumbnailClick(i)}
          >
            <Image src={img.src} alt={img.alt} width={80} height={80} />
            {img.type === 'video' && (
              <span className={styles.playIcon} aria-hidden="true">&#9654;</span>
            )}
          </button>
        ))}
      </div>
    </section>
  );
}
```

### ProductInfo.tsx

```tsx
'use client';

import { useState, useCallback } from 'react';
import styles from './product-detail.module.css';

interface ProductInfoProps {
  brand: string;
  name: string;
  price: number;
  originalPrice: number;
  rating: number;
  reviewCount: number;
  options: { label: string; value: string; available: boolean; color?: string }[];
  badges: string[];
  points: number;
  deliveryInfo: string;
}

/** 제품 기본 정보 + CTA 컴포넌트 */
export default function ProductInfo({
  brand, name, price, originalPrice,
  rating, reviewCount, options, badges,
  points, deliveryInfo,
}: ProductInfoProps) {
  const [selectedOption, setSelectedOption] = useState(
    options.find((o) => o.available)?.value || ''
  );
  const [quantity, setQuantity] = useState(1);
  const discountRate = Math.round((1 - price / originalPrice) * 100);

  const handleQuantityChange = useCallback((delta: number) => {
    setQuantity((prev) => Math.max(1, Math.min(99, prev + delta)));
  }, []);

  return (
    <section className={styles.info} aria-label="제품 정보">
      <a href={`/brand/${brand}`} className={styles.infoBrand}>{brand}</a>
      <h1 className={styles.infoTitle}>{name}</h1>

      {/* 평점 */}
      <div className={styles.infoRating} aria-label={`평점 ${rating}점, 리뷰 ${reviewCount}개`}>
        <span className={styles.infoStars} aria-hidden="true">
          {'★'.repeat(Math.floor(rating))}{'☆'.repeat(5 - Math.floor(rating))}
        </span>
        <span>{rating}</span>
        <a href="#reviews">({reviewCount.toLocaleString()})</a>
      </div>

      {/* 가격 */}
      <div className={styles.infoPriceWrap}>
        <span className={styles.infoDiscountBadge}>{discountRate}%</span>
        <strong className={styles.infoPrice}>
          {price.toLocaleString()}<small>원</small>
        </strong>
        <del className={styles.infoOriginalPrice}>
          {originalPrice.toLocaleString()}원
        </del>
      </div>

      {/* 배지 */}
      <div className={styles.infoBadges}>
        {badges.map((badge) => (
          <span key={badge} className={styles.infoBadge}>{badge}</span>
        ))}
      </div>

      {/* 배송 */}
      <p className={styles.infoDelivery}>{deliveryInfo}</p>

      {/* 적립금 */}
      <p className={styles.infoPoints}>
        적립 <strong>{points.toLocaleString()}P</strong>
      </p>

      {/* 옵션 선택 */}
      <fieldset className={styles.infoOptions}>
        <legend>옵션 선택</legend>
        <div className={styles.infoSwatches}>
          {options.map((opt) => (
            <button
              key={opt.value}
              className={`${styles.infoSwatch} ${
                selectedOption === opt.value ? styles.infoSwatchActive : ''
              } ${!opt.available ? styles.infoSwatchDisabled : ''}`}
              disabled={!opt.available}
              aria-label={`${opt.label}${!opt.available ? ' 품절' : ''}`}
              onClick={() => opt.available && setSelectedOption(opt.value)}
              style={opt.color ? { backgroundColor: opt.color } : undefined}
            />
          ))}
        </div>
      </fieldset>

      {/* 수량 */}
      <div className={styles.infoQuantity}>
        <label htmlFor="qty">수량</label>
        <div className={styles.infoQtyControl}>
          <button onClick={() => handleQuantityChange(-1)} aria-label="수량 감소">-</button>
          <input
            id="qty"
            type="number"
            value={quantity}
            min={1}
            max={99}
            readOnly
            aria-label="수량"
          />
          <button onClick={() => handleQuantityChange(1)} aria-label="수량 증가">+</button>
        </div>
      </div>

      {/* CTA */}
      <div className={styles.infoCta}>
        <button className={styles.btnSecondary}>장바구니 담기</button>
        <button className={styles.btnPrimary}>바로 구매하기</button>
      </div>
    </section>
  );
}
```

### FAQAccordion.tsx

```tsx
'use client';

import { useState, useCallback } from 'react';
import styles from './product-detail.module.css';

interface FAQItem {
  question: string;
  answer: string;
}

interface FAQAccordionProps {
  items: FAQItem[];
}

/** FAQ 아코디언 컴포넌트 */
export default function FAQAccordion({ items }: FAQAccordionProps) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  const toggle = useCallback((index: number) => {
    setOpenIndex((prev) => (prev === index ? null : index));
  }, []);

  return (
    <section className={styles.faq} aria-label="자주 묻는 질문">
      <h2 className={styles.faqTitle}>자주 묻는 질문</h2>
      <div className={styles.faqList}>
        {items.map((item, i) => (
          <div key={i} className={styles.faqItem}>
            <button
              className={styles.faqQuestion}
              aria-expanded={openIndex === i}
              aria-controls={`faq-answer-${i}`}
              onClick={() => toggle(i)}
            >
              <span>{item.question}</span>
              <span className={styles.faqIcon} aria-hidden="true">
                {openIndex === i ? '-' : '+'}
              </span>
            </button>
            <div
              id={`faq-answer-${i}`}
              className={`${styles.faqAnswer} ${openIndex === i ? styles.faqAnswerOpen : ''}`}
              hidden={openIndex !== i}
            >
              <p>{item.answer}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
```

---

## 9. CSS 변수 정의 템플릿

```css
/* 상세 페이지 디자인 토큰 */
:root {
  /* 색상 */
  --pd-primary: #FF6B35;
  --pd-primary-hover: #E55A2B;
  --pd-primary-light: #FFF3EE;
  --pd-accent: #FF0000;
  --pd-accent-light: #FFF0F0;
  --pd-bg-primary: #FFFFFF;
  --pd-bg-secondary: #F8F8F8;
  --pd-text-primary: #1A1A1A;
  --pd-text-secondary: #666666;
  --pd-text-tertiary: #999999;
  --pd-border: #E0E0E0;
  --pd-star: #FFD700;
  --pd-success: #00B894;
  --pd-warning: #FDCB6E;
  --pd-error: #E17055;

  /* 타이포그래피 */
  --pd-font: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
  --pd-font-xs: 12px;
  --pd-font-sm: 14px;
  --pd-font-base: 16px;
  --pd-font-lg: 18px;
  --pd-font-xl: 24px;
  --pd-font-2xl: 32px;
  --pd-font-3xl: 36px;

  /* 간격 */
  --pd-space-xs: 4px;
  --pd-space-sm: 8px;
  --pd-space-md: 16px;
  --pd-space-lg: 24px;
  --pd-space-xl: 32px;
  --pd-space-2xl: 48px;

  /* 레이아웃 */
  --pd-max-width: 860px;
  --pd-border-radius: 8px;
  --pd-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  --pd-transition: 0.3s ease;
}
```

---

## 10. 모바일 반응형 미디어쿼리 템플릿

```css
/* 모바일 기본 (375px~) */
.product-detail {
  max-width: 100%;
  padding: 0 var(--pd-space-md);
  font-family: var(--pd-font);
}

/* 탭 메뉴 스티키 */
.tab-menu {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--pd-bg-primary);
  border-bottom: 1px solid var(--pd-border);
  display: flex;
}
.tab-menu__tab {
  flex: 1;
  padding: var(--pd-space-md) 0;
  text-align: center;
  border: none;
  background: none;
  font-size: var(--pd-font-base);
  cursor: pointer;
  color: var(--pd-text-secondary);
}
.tab-menu__tab--active {
  color: var(--pd-text-primary);
  font-weight: 700;
  border-bottom: 2px solid var(--pd-primary);
}

/* 모바일 하단 고정 바 */
.mobile-bottom-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  gap: var(--pd-space-sm);
  padding: var(--pd-space-sm) var(--pd-space-md);
  background: var(--pd-bg-primary);
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.1);
  z-index: 1000;
}
.mobile-bottom-bar__cart {
  flex: 2;
  height: 48px;
  border: 2px solid var(--pd-primary);
  border-radius: var(--pd-border-radius);
  background: var(--pd-bg-primary);
  color: var(--pd-primary);
  font-weight: 600;
  cursor: pointer;
}
.mobile-bottom-bar__buy {
  flex: 3;
  height: 48px;
  border: none;
  border-radius: var(--pd-border-radius);
  background: var(--pd-primary);
  color: #FFFFFF;
  font-weight: 600;
  cursor: pointer;
}

/* FAQ 아코디언 */
.faq__question {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: var(--pd-space-md);
  border: none;
  border-bottom: 1px solid var(--pd-border);
  background: none;
  font-size: var(--pd-font-base);
  text-align: left;
  cursor: pointer;
}
.faq__answer {
  padding: var(--pd-space-md);
  background: var(--pd-bg-secondary);
  overflow: hidden;
  transition: max-height var(--pd-transition);
}

/* 후기 평점 분포 바 */
.reviews__bar {
  flex: 1;
  height: 8px;
  background: var(--pd-bg-secondary);
  border-radius: 4px;
  margin: 0 var(--pd-space-sm);
}
.reviews__bar-fill {
  height: 100%;
  background: var(--pd-star);
  border-radius: 4px;
}

/* 태블릿 (768px~) */
@media (min-width: 768px) {
  .product-detail {
    max-width: var(--pd-max-width);
    margin: 0 auto;
  }

  /* 히어로: 이미지 + 정보 2컬럼 */
  .product-detail__top {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--pd-space-xl);
  }

  /* 관련 제품: 4컬럼 그리드 */
  .related__grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: var(--pd-space-md);
  }

  /* 모바일 하단 바 숨김 */
  .mobile-bottom-bar {
    display: none;
  }
}

/* 데스크톱 (1024px~) */
@media (min-width: 1024px) {
  .product-detail {
    max-width: var(--pd-max-width);
  }

  /* 이미지 호버 줌 */
  .product-hero__img:hover {
    cursor: zoom-in;
  }
}
```

---

## 11. Schema.org Product JSON-LD 템플릿

```html
<!-- 구조화 데이터: 검색 엔진 리치 스니펫 노출 -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "[제품명]",
  "image": [
    "https://example.com/images/main-01.webp",
    "https://example.com/images/main-02.webp",
    "https://example.com/images/main-03.webp"
  ],
  "description": "[제품 설명 160자 이내]",
  "sku": "[SKU 코드]",
  "brand": {
    "@type": "Brand",
    "name": "[브랜드명]"
  },
  "offers": {
    "@type": "Offer",
    "url": "https://example.com/product/001",
    "priceCurrency": "KRW",
    "price": "89900",
    "priceValidUntil": "2026-12-31",
    "availability": "https://schema.org/InStock",
    "itemCondition": "https://schema.org/NewCondition",
    "seller": {
      "@type": "Organization",
      "name": "[판매자명]"
    },
    "shippingDetails": {
      "@type": "OfferShippingDetails",
      "shippingRate": {
        "@type": "MonetaryAmount",
        "value": "0",
        "currency": "KRW"
      },
      "deliveryTime": {
        "@type": "ShippingDeliveryTime",
        "handlingTime": {
          "@type": "QuantitativeValue",
          "minValue": 0,
          "maxValue": 1,
          "unitCode": "DAY"
        },
        "transitTime": {
          "@type": "QuantitativeValue",
          "minValue": 1,
          "maxValue": 2,
          "unitCode": "DAY"
        }
      },
      "shippingDestination": {
        "@type": "DefinedRegion",
        "addressCountry": "KR"
      }
    }
  },
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "4.8",
    "bestRating": "5",
    "worstRating": "1",
    "ratingCount": "3241",
    "reviewCount": "3241"
  },
  "review": [
    {
      "@type": "Review",
      "reviewRating": {
        "@type": "Rating",
        "ratingValue": "5",
        "bestRating": "5"
      },
      "author": {
        "@type": "Person",
        "name": "홍*동"
      },
      "datePublished": "2026-04-05",
      "reviewBody": "[후기 텍스트]"
    }
  ]
}
</script>
```
