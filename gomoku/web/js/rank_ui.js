/**
 * 天梯段位徽章与排位星级渲染组件模块。
 * 
 * 严格遵循无蓝紫色规范，采用东方古铜、流银、璀璨真金与朱砂印记视觉配色。
 * 所有代码注释采用中文。
 */

class RankUIHelper {
  /**
   * 生成段位专属小段星级 HTML 视图。
   * @param {string} tier - 大段名称（如 "荣耀黄金"）
   * @param {number} subTier - 小段序号（1 到 5）
   * @param {number} stars - 当前星数
   * @param {number} maxStars - 当前小段满星数
   * @returns {string} HTML 字符串
   */
  static renderStars(tier, subTier, stars, maxStars = 4) {
    // 王者及以上直接显示大星 + 累计数字
    if (tier.includes('王者')) {
      return `
        <div style="display:inline-flex;align-items:center;gap:6px;">
          <span style="font-size:1.6rem;color:#F59E0B;text-shadow:0 0 10px rgba(245,158,11,0.6);">★</span>
          <span style="font-size:1.2rem;font-weight:bold;color:#FAF7EE;">x ${stars}</span>
        </div>
      `;
    }

    let html = '<div style="display:inline-flex;gap:4px;">';
    for (let i = 0; i < maxStars; i++) {
      if (i < stars) {
        html += '<span style="color:#F59E0B;text-shadow:0 0 8px rgba(245,158,11,0.5);">★</span>';
      } else {
        html += '<span style="color:#52473D;">☆</span>';
      }
    }
    html += '</div>';
    return html;
  }

  /**
   * 获取各段位的主题专属色标（严格排除蓝紫色）。
   * @param {string} tier - 段位名称
   * @returns {{badgeBg: string, textColor: string, border: string}}
   */
  static getTierTheme(tier) {
    if (tier.includes('青铜')) {
      return {
        badgeBg: 'linear-gradient(135deg, #78350F, #B45309)',
        textColor: '#FEF3C7',
        border: '#92400E',
      };
    }
    if (tier.includes('白银')) {
      return {
        badgeBg: 'linear-gradient(135deg, #4B5563, #9CA3AF)',
        textColor: '#FFFFFF',
        border: '#D1D5DB',
      };
    }
    if (tier.includes('黄金')) {
      return {
        badgeBg: 'linear-gradient(135deg, #B45309, #F59E0B)',
        textColor: '#161412',
        border: '#FBBF24',
      };
    }
    if (tier.includes('铂金')) {
      return {
        badgeBg: 'linear-gradient(135deg, #065F46, #10B981)',
        textColor: '#FFFFFF',
        border: '#34D399',
      };
    }
    if (tier.includes('钻石')) {
      return {
        badgeBg: 'linear-gradient(135deg, #854D0E, #EAB308)',
        textColor: '#1A1816',
        border: '#FACC15',
      };
    }
    if (tier.includes('星耀')) {
      return {
        badgeBg: 'linear-gradient(135deg, #991B1B, #DC2626)',
        textColor: '#FFFFFF',
        border: '#F87171',
      };
    }
    // 王者梯队
    return {
      badgeBg: 'linear-gradient(135deg, #92400E 0%, #D4AF37 50%, #F59E0B 100%)',
      textColor: '#161412',
      border: '#FDE047',
    };
  }

  /**
   * 格式化勇者积分上限值。
   */
  static getBravePointsCap(tier) {
    if (tier.includes('青铜')) return 100;
    if (tier.includes('白银')) return 120;
    if (tier.includes('黄金')) return 150;
    if (tier.includes('铂金')) return 200;
    if (tier.includes('王者')) return 400;
    return 300;
  }
}

window.RankUIHelper = RankUIHelper;
